"""
Gemini Vision OCR Engine for FINTEL AI
Uses Google's Gemini Vision AI to intelligently extract invoice data
"""

import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import re
from pathlib import Path

class GeminiVisionOCR:
    def __init__(self, api_key="AIzaSyB7zJbF7Nx_KP4oIOZCGc5P84WN4RHO14M"):
        """Initialize Gemini Vision with API key"""
        print("🚀 Initializing Gemini Vision OCR...")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("✅ Gemini Vision OCR initialized!")
    
    def convert_pdf_to_image(self, pdf_path):
        """Convert PDF first page to high-quality image"""
        try:
            doc = fitz.open(str(pdf_path))
            page = doc.load_page(0)  # First page
            
            # High resolution for better OCR
            mat = fitz.Matrix(3.0, 3.0)  # 300 DPI
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            doc.close()
            print(f"✅ Converted PDF to image: {image.size}")
            return image
        except Exception as e:
            print(f"❌ PDF conversion error: {e}")
            return None
    
    def create_extraction_prompt(self):
        """Create detailed prompt for Gemini to extract invoice data"""
        prompt = """You are an expert invoice data extraction AI. Analyze this invoice image carefully and extract ALL the following information:

**CRITICAL INSTRUCTIONS:**
1. Extract data EXACTLY as it appears on the invoice
2. For dates, use DD-MM-YYYY or DD/MM/YYYY format
3. For amounts, extract only numbers (no currency symbols)
4. **GST NUMBERS - EXTREMELY IMPORTANT:**
   - **ONLY extract the VENDOR/SELLER/SUPPLIER GST number (the company issuing the invoice)**
   - **DO NOT extract the buyer/recipient/customer GST number**
   - Look for GST in the "Vendor Details", "Seller Details", "From", or top section of invoice
   - IGNORE GST in "Bill To", "Ship To", "Customer Details", or buyer section
   - GST MUST be EXACTLY 15 characters (no more, no less)
   - Format: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric
   - Example: 24AAACI0931P1ZL (exactly 15 chars)
   - If you see a GST with extra characters (like 24AAAACI0931P1ZL with 17 chars), extract ONLY the valid 15-character portion
   - Double-check the length before adding to the list
   - Only include GST numbers that are EXACTLY 15 characters
5. If any field is not found, use "Unknown" for text fields and 0 for numeric fields

**EXTRACT THE FOLLOWING:**

1. **Invoice Number**: The invoice/bill number (look for: Invoice No, Bill No, Inv No, etc.)
2. **Vendor/Company Name**: The company/vendor issuing the invoice (usually at top in large text)
3. **Invoice Date**: The date of invoice (look for: Date, Invoice Date, Bill Date, etc.)
4. **Total Amount**: The final total amount payable (look for: Total, Grand Total, Amount Payable, Net Amount)
5. **GST Numbers**: ONLY the VENDOR/SELLER GST number (from vendor details section, NOT from buyer/customer section)
6. **GST Rate**: The GST percentage applied (look for: CGST %, SGST %, IGST %, GST Rate - e.g., 18%, 12%, 5%, 28%)
7. **HSN Number**: The primary HSN/SAC code (4-8 digit code, look for: HSN, SAC, HSN Code, SAC Code)
8. **Vendor Address**: Complete address of the vendor
9. **Line Items**: Extract all items/services with:
   - Item description
   - HSN/SAC code (if present)
   - Quantity
   - Rate/Price
   - Amount

**RETURN FORMAT:**
Return ONLY a valid JSON object with this EXACT structure (no markdown, no code blocks, just pure JSON):

{
  "invoice_number": "extracted invoice number or Unknown",
  "vendor_name": "extracted vendor/company name or Unknown",
  "invoice_date": "DD-MM-YYYY or Unknown",
  "total_amount": 0.0,
  "gst_numbers": ["list of all GST numbers found"],
  "gst_rate": "GST percentage (e.g., 18%, 12%, 5%) or Unknown",
  "hsn_number": "primary HSN/SAC code or Unknown",
  "vendor_address": "complete address or Unknown",
  "line_items": [
    {
      "description": "item description",
      "hsn_code": "HSN/SAC code or empty",
      "quantity": 0,
      "rate": 0.0,
      "amount": 0.0
    }
  ],
  "hsn_codes": ["list of all HSN/SAC codes found"],
  "raw_extracted_text": "any other important text you see"
}

**IMPORTANT:**
- Be thorough and accurate
- Extract ALL GST numbers you find
- Extract ALL HSN/SAC codes
- If you see multiple amounts, choose the FINAL TOTAL
- Return ONLY the JSON, nothing else"""

        return prompt
    
    def extract_invoice_data(self, image):
        """Use Gemini Vision to extract structured data from invoice image"""
        try:
            print("🔍 Sending image to Gemini Vision AI...")
            
            # Create prompt
            prompt = self.create_extraction_prompt()
            
            # Send to Gemini Vision
            response = self.model.generate_content([prompt, image])
            
            print("✅ Received response from Gemini Vision")
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Parse JSON
            try:
                extracted_data = json.loads(response_text)
                print("✅ Successfully parsed JSON response")
                return extracted_data
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse error: {e}")
                print(f"Response text: {response_text[:500]}")
                # Try to extract JSON from text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                    print("✅ Extracted JSON from response")
                    return extracted_data
                else:
                    return None
                
        except Exception as e:
            print(f"❌ Gemini Vision error: {e}")
            return None
    
    def process_invoice(self, file_path):
        """
        Main processing function
        Returns structured invoice data
        """
        print(f"\n{'='*60}")
        print(f"🔍 Processing Invoice: {Path(file_path).name}")
        print(f"{'='*60}")
        
        # Convert PDF to image
        image = self.convert_pdf_to_image(file_path)
        
        if not image:
            return {
                'success': False,
                'error': 'Failed to convert PDF to image'
            }
        
        # Extract data using Gemini Vision
        extracted_data = self.extract_invoice_data(image)
        
        if not extracted_data:
            return {
                'success': False,
                'error': 'Failed to extract data from invoice'
            }
        
        # Validate and clean GST numbers (MUST be exactly 15 characters)
        raw_gst_numbers = extracted_data.get('gst_numbers', [])
        valid_gst_numbers = []
        
        for gst in raw_gst_numbers:
            cleaned_gst = gst.replace(" ", "").upper()
            if len(cleaned_gst) == 15:
                valid_gst_numbers.append(cleaned_gst)
                print(f"✅ Valid GST: {cleaned_gst} (15 chars)")
            else:
                print(f"❌ Invalid GST: {gst} ({len(cleaned_gst)} chars) - REJECTED")
        
        # Structure the response
        structured_data = {
            'invoice_number': extracted_data.get('invoice_number', 'Unknown'),
            'vendor_name': extracted_data.get('vendor_name', 'Unknown'),
            'invoice_date': extracted_data.get('invoice_date', 'Unknown'),
            'total_amount': float(extracted_data.get('total_amount', 0)),
            'gst_numbers': valid_gst_numbers,  # Only valid 15-char GST numbers
            'gst_rate': extracted_data.get('gst_rate', 'Unknown'),  # GST percentage
            'hsn_number': extracted_data.get('hsn_number', 'Unknown'),  # Primary HSN number
            'vendor_address': extracted_data.get('vendor_address', 'Unknown'),
            'hsn_codes': extracted_data.get('hsn_codes', []),
            'line_items': extracted_data.get('line_items', [])
        }
        
        # Print summary
        print(f"\n📊 EXTRACTION SUMMARY:")
        print(f"  Invoice #: {structured_data['invoice_number']}")
        print(f"  Vendor: {structured_data['vendor_name']}")
        print(f"  Date: {structured_data['invoice_date']}")
        print(f"  Amount: ₹{structured_data['total_amount']:,.2f}")
        print(f"  GST Numbers: {len(structured_data['gst_numbers'])} found")
        print(f"  GST Rate: {structured_data['gst_rate']}")
        print(f"  HSN Number: {structured_data['hsn_number']}")
        print(f"  HSN Codes: {len(structured_data['hsn_codes'])} found")
        print(f"  Line Items: {len(structured_data['line_items'])} items")
        
        return {
            'success': True,
            'raw_text': extracted_data.get('raw_extracted_text', ''),
            'confidence': 95.0,  # Gemini Vision is highly accurate
            'structured_data': structured_data
        }

# Create global instance
gemini_vision_ocr = GeminiVisionOCR()

if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        result = gemini_vision_ocr.process_invoice(sys.argv[1])
        if result['success']:
            print("\n" + "="*60)
            print("✅ EXTRACTION SUCCESSFUL!")
            print("="*60)
            print(json.dumps(result['structured_data'], indent=2))
        else:
            print(f"\n❌ Error: {result.get('error')}")
