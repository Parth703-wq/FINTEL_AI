"""
MongoDB Database Module for FINTEL AI
Handles invoice storage, vendor tracking, and anomaly detection
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

class FintelDatabase:
    def __init__(self, connection_string="mongodb://localhost:27017/"):
        """Initialize MongoDB connection"""
        self.client = MongoClient(connection_string)
        self.db = self.client['fintel_ai']
        
        # Collections
        self.invoices = self.db['invoices']
        self.vendors = self.db['vendors']
        self.anomalies = self.db['anomalies']
        
        # Create indexes for faster queries
        self._create_indexes()
        
        print("✅ MongoDB connected successfully!")
        print(f"   Database: fintel_ai")
        print(f"   Collections: invoices, vendors, anomalies")
    
    def _create_indexes(self):
        """Create indexes for optimized queries"""
        # Invoice indexes
        self.invoices.create_index([("invoiceNumber", ASCENDING)], unique=False)
        self.invoices.create_index([("gstNumber", ASCENDING)])
        self.invoices.create_index([("vendorName", ASCENDING)])
        self.invoices.create_index([("uploadDate", DESCENDING)])
        
        # Vendor indexes
        self.vendors.create_index([("gstNumber", ASCENDING)], unique=True)
        self.vendors.create_index([("vendorName", ASCENDING)])
        
        # Anomaly indexes
        self.anomalies.create_index([("invoiceId", ASCENDING)])
        self.anomalies.create_index([("anomalyType", ASCENDING)])
        self.anomalies.create_index([("severity", ASCENDING)])
    
    def store_invoice(self, invoice_data: Dict[str, Any]) -> str:
        """
        Store invoice in database
        Returns: invoice_id
        """
        invoice_doc = {
            'filename': invoice_data.get('filename'),
            'uploadDate': datetime.now(),
            'invoiceNumber': invoice_data.get('invoice_number'),
            'vendorName': invoice_data.get('vendor_name'),
            'gstNumber': invoice_data.get('gst_numbers', [])[0] if invoice_data.get('gst_numbers') else None,
            'allGstNumbers': invoice_data.get('gst_numbers', []),
            'totalAmount': float(invoice_data.get('total_amount', 0)),
            'invoiceDate': invoice_data.get('invoice_date'),
            'hsnCodes': invoice_data.get('hsn_sac_codes', []),
            'itemDescriptions': invoice_data.get('item_descriptions', []),
            'quantities': invoice_data.get('quantities', []),
            'ocrConfidence': float(invoice_data.get('ocr_confidence', 0)),
            'complianceResults': invoice_data.get('compliance_results', {}),
            'mlPrediction': invoice_data.get('ml_prediction', {}),
            'rawText': invoice_data.get('raw_text', '')[:1000]  # Store first 1000 chars
        }
        
        result = self.invoices.insert_one(invoice_doc)
        invoice_id = str(result.inserted_id)
        
        # Update vendor statistics
        self._update_vendor_stats(invoice_doc)
        
        print(f"✅ Invoice stored: {invoice_doc['invoiceNumber']} (ID: {invoice_id})")
        return invoice_id
    
    def _update_vendor_stats(self, invoice_doc: Dict):
        """Update or create vendor statistics"""
        gst_number = invoice_doc.get('gstNumber')
        vendor_name = invoice_doc.get('vendorName')
        
        if not gst_number or gst_number == 'Unknown':
            return
        
        vendor = self.vendors.find_one({'gstNumber': gst_number})
        
        if vendor:
            # Update existing vendor
            self.vendors.update_one(
                {'gstNumber': gst_number},
                {
                    '$inc': {
                        'totalInvoices': 1,
                        'totalAmount': invoice_doc.get('totalAmount', 0)
                    },
                    '$set': {
                        'lastInvoiceDate': datetime.now(),
                        'vendorName': vendor_name  # Update in case name changed
                    }
                }
            )
        else:
            # Create new vendor
            self.vendors.insert_one({
                'gstNumber': gst_number,
                'vendorName': vendor_name,
                'totalInvoices': 1,
                'totalAmount': invoice_doc.get('totalAmount', 0),
                'firstInvoiceDate': datetime.now(),
                'lastInvoiceDate': datetime.now()
            })
    
    def detect_anomalies(self, invoice_data: Dict[str, Any], invoice_id: str) -> List[Dict]:
        """
        Detect anomalies by comparing with historical data
        Returns: List of detected anomalies
        """
        from bson import ObjectId
        anomalies = []
        
        # Convert invoice_id to ObjectId for comparison
        try:
            obj_id = ObjectId(invoice_id)
        except:
            obj_id = invoice_id
        
        # 1. Check for duplicate invoice number
        duplicate = self.invoices.find_one({
            'invoiceNumber': invoice_data.get('invoice_number'),
            '_id': {'$ne': obj_id}
        })
        if duplicate:
            anomalies.append({
                'type': 'DUPLICATE_INVOICE',
                'severity': 'HIGH',
                'description': f"Duplicate invoice number: {invoice_data.get('invoice_number')}",
                'relatedInvoiceId': str(duplicate['_id'])
            })
        
        # 2. Check for GST number with different vendor name
        gst_number = invoice_data.get('gst_numbers', [])[0] if invoice_data.get('gst_numbers') else None
        if gst_number:
            different_vendor = self.invoices.find_one({
                'gstNumber': gst_number,
                'vendorName': {'$ne': invoice_data.get('vendor_name')},
                '_id': {'$ne': obj_id}
            })
            if different_vendor:
                anomalies.append({
                    'type': 'GST_VENDOR_MISMATCH',
                    'severity': 'HIGH',
                    'description': f"GST {gst_number} used by different vendor: {different_vendor['vendorName']} vs {invoice_data.get('vendor_name')}",
                    'relatedInvoiceId': str(different_vendor['_id'])
                })
        
        # 3. Check for unusual amount from same vendor
        vendor_name = invoice_data.get('vendor_name')
        if vendor_name and vendor_name != 'Unknown':
            # Get average amount for this vendor
            pipeline = [
                {'$match': {'vendorName': vendor_name}},
                {'$group': {
                    '_id': None,
                    'avgAmount': {'$avg': '$totalAmount'},
                    'maxAmount': {'$max': '$totalAmount'},
                    'minAmount': {'$min': '$totalAmount'}
                }}
            ]
            stats = list(self.vendors_stats(vendor_name))
            if stats:
                avg_amount = stats[0].get('avgAmount', 0)
                current_amount = float(invoice_data.get('total_amount', 0))
                
                # If amount is 3x more than average
                if avg_amount > 0 and current_amount > (avg_amount * 3):
                    anomalies.append({
                        'type': 'UNUSUAL_AMOUNT',
                        'severity': 'MEDIUM',
                        'description': f"Amount ₹{current_amount} is 3x higher than vendor average ₹{avg_amount:.2f}"
                    })
        
        # 4. Check for same HSN code with very different price
        hsn_codes = invoice_data.get('hsn_sac_codes', [])
        if hsn_codes:
            for hsn in hsn_codes[:3]:  # Check first 3 HSN codes
                similar_invoices = list(self.invoices.find({
                    'hsnCodes': hsn,
                    '_id': {'$ne': invoice_id}
                }).limit(10))
                
                if len(similar_invoices) >= 3:
                    amounts = [inv['totalAmount'] for inv in similar_invoices if inv.get('totalAmount', 0) > 0]
                    if amounts:
                        avg_hsn_amount = sum(amounts) / len(amounts)
                        current_amount = float(invoice_data.get('total_amount', 0))
                        
                        # If amount differs by more than 50%
                        if avg_hsn_amount > 0 and abs(current_amount - avg_hsn_amount) > (avg_hsn_amount * 0.5):
                            anomalies.append({
                                'type': 'HSN_PRICE_DEVIATION',
                                'severity': 'MEDIUM',
                                'description': f"HSN {hsn}: Amount ₹{current_amount} deviates significantly from historical average ₹{avg_hsn_amount:.2f}"
                            })
                            break  # Only report once
        
        # Store anomalies in database
        for anomaly in anomalies:
            self.anomalies.insert_one({
                'invoiceId': invoice_id,
                'invoiceNumber': invoice_data.get('invoice_number'),
                'anomalyType': anomaly['type'],
                'severity': anomaly['severity'],
                'description': anomaly['description'],
                'detectedDate': datetime.now(),
                'relatedInvoiceId': anomaly.get('relatedInvoiceId')
            })
        
        return anomalies
    
    def vendors_stats(self, vendor_name: str) -> List[Dict]:
        """Get statistics for a vendor"""
        pipeline = [
            {'$match': {'vendorName': vendor_name}},
            {'$group': {
                '_id': None,
                'avgAmount': {'$avg': '$totalAmount'},
                'maxAmount': {'$max': '$totalAmount'},
                'minAmount': {'$min': '$totalAmount'},
                'totalInvoices': {'$sum': 1}
            }}
        ]
        return list(self.invoices.aggregate(pipeline))
    
    def get_invoice_history(self, limit: int = 50) -> List[Dict]:
        """Get recent invoice history"""
        invoices = list(self.invoices.find().sort('uploadDate', DESCENDING).limit(limit))
        
        # Convert ObjectId to string
        for inv in invoices:
            inv['_id'] = str(inv['_id'])
            inv['uploadDate'] = inv['uploadDate'].isoformat() if inv.get('uploadDate') else None
        
        return invoices
    
    def get_vendor_list(self) -> List[Dict]:
        """Get list of all vendors"""
        vendors = list(self.vendors.find().sort('totalAmount', DESCENDING))
        
        for vendor in vendors:
            vendor['_id'] = str(vendor['_id'])
            vendor['firstInvoiceDate'] = vendor['firstInvoiceDate'].isoformat() if vendor.get('firstInvoiceDate') else None
            vendor['lastInvoiceDate'] = vendor['lastInvoiceDate'].isoformat() if vendor.get('lastInvoiceDate') else None
        
        return vendors
    
    def get_anomalies(self, severity: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get detected anomalies"""
        query = {}
        if severity:
            query['severity'] = severity
        
        anomalies = list(self.anomalies.find(query).sort('detectedDate', DESCENDING).limit(limit))
        
        for anomaly in anomalies:
            anomaly['_id'] = str(anomaly['_id'])
            anomaly['detectedDate'] = anomaly['detectedDate'].isoformat() if anomaly.get('detectedDate') else None
        
        return anomalies
    
    def get_dashboard_stats(self) -> Dict:
        """Get statistics for dashboard"""
        total_invoices = self.invoices.count_documents({})
        total_vendors = self.vendors.count_documents({})
        total_anomalies = self.anomalies.count_documents({})
        high_severity_anomalies = self.anomalies.count_documents({'severity': 'HIGH'})
        
        # Total amount processed
        pipeline = [
            {'$group': {
                '_id': None,
                'totalAmount': {'$sum': '$totalAmount'}
            }}
        ]
        amount_result = list(self.invoices.aggregate(pipeline))
        total_amount = amount_result[0]['totalAmount'] if amount_result else 0
        
        return {
            'totalInvoices': total_invoices,
            'totalVendors': total_vendors,
            'totalAnomalies': total_anomalies,
            'highSeverityAnomalies': high_severity_anomalies,
            'totalAmountProcessed': total_amount
        }
    
    def close(self):
        """Close database connection"""
        self.client.close()
        print("MongoDB connection closed")


# Test connection
if __name__ == "__main__":
    db = FintelDatabase()
    print("\n📊 Database Stats:")
    stats = db.get_dashboard_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    db.close()
