# 🚀 FINTEL AI - Deployment Guide

Complete guide to deploy FINTEL AI in production or development environments.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **MongoDB 6.0+** - [Download](https://www.mongodb.com/try/download/community)
- **Git** - [Download](https://git-scm.com/downloads)

### Required API Keys

1. **Google Gemini API Key**
   - Visit: https://aistudio.google.com/app/apikey
   - Create new API key
   - Free tier available

2. **RapidAPI GST Insights Key**
   - Visit: https://rapidapi.com/gst-insights-gst-insights-default/api/gst-insights
   - Subscribe to API (Free tier available)
   - Copy API key from dashboard

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/Parth703-wq/HackOps7.git
cd HackOps7
```

### Step 2: Backend Setup

```bash
# Navigate to backend
cd AI-Agent

# Install Python dependencies
pip install -r requirements_free.txt

# Or use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements_free.txt
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your API keys
# Use any text editor (notepad, vim, nano, etc.)
notepad .env  # Windows
nano .env     # Linux/Mac
```

**Add your keys:**
```env
GEMINI_API_KEY=AIzaSy...your-actual-key
RAPIDAPI_KEY=abc123...your-actual-key
```

### Step 4: Frontend Setup

```bash
# Navigate to frontend
cd ../Frontend

# Install dependencies
npm install

# Or use yarn
yarn install
```

### Step 5: Start MongoDB

**Windows:**
```bash
# Start MongoDB service
net start MongoDB

# Or run manually
mongod
```

**Linux/Mac:**
```bash
sudo systemctl start mongod

# Or run manually
mongod --dbpath /path/to/data
```

### Step 6: Run the Application

**Terminal 1 - Backend:**
```bash
cd AI-Agent
python fintel_api_fixed.py
```

**Terminal 2 - Frontend:**
```bash
cd Frontend
npm run dev
```

**Access Application:**
```
Frontend: http://localhost:8080
Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs
```

---

## Production Deployment

### Option 1: Docker Deployment (Recommended)

**Coming Soon** - Docker configuration in progress

### Option 2: Manual Server Deployment

#### Backend Deployment

1. **Install Dependencies:**
```bash
pip install -r requirements_free.txt
```

2. **Configure Production Environment:**
```bash
cp .env.example .env
# Add production API keys
```

3. **Run with Gunicorn:**
```bash
pip install gunicorn
gunicorn fintel_api_fixed:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

4. **Setup Systemd Service (Linux):**
```bash
sudo nano /etc/systemd/system/fintel-api.service
```

```ini
[Unit]
Description=FINTEL AI API
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/AI-Agent
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn fintel_api_fixed:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable fintel-api
sudo systemctl start fintel-api
```

#### Frontend Deployment

1. **Build for Production:**
```bash
cd Frontend
npm run build
```

2. **Serve with Nginx:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/Frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Environment Configuration

### Development Environment

```env
# .env for development
GEMINI_API_KEY=your-dev-key
RAPIDAPI_KEY=your-dev-key
MONGODB_URI=mongodb://localhost:27017/
API_HOST=0.0.0.0
API_PORT=8000
```

### Production Environment

```env
# .env for production
GEMINI_API_KEY=your-prod-key
RAPIDAPI_KEY=your-prod-key
MONGODB_URI=mongodb://production-server:27017/
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Troubleshooting

### Common Issues

#### 1. MongoDB Connection Error

**Error:** `pymongo.errors.ServerSelectionTimeoutError`

**Solution:**
```bash
# Check if MongoDB is running
sudo systemctl status mongod  # Linux
net start MongoDB             # Windows

# Check MongoDB connection
mongo --eval "db.adminCommand('ping')"
```

#### 2. API Key Invalid

**Error:** `Invalid API key` or `401 Unauthorized`

**Solution:**
- Verify API keys in `.env` file
- Ensure no extra spaces or quotes
- Check API key is active on provider dashboard

#### 3. Port Already in Use

**Error:** `Address already in use: 8000`

**Solution:**
```bash
# Find process using port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

#### 4. Frontend Build Errors

**Error:** `Module not found` or `npm ERR!`

**Solution:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Or use legacy peer deps
npm install --legacy-peer-deps
```

#### 5. Python Module Not Found

**Error:** `ModuleNotFoundError: No module named 'xyz'`

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements_free.txt

# Or install specific module
pip install module-name
```

---

## Performance Optimization

### Backend Optimization

1. **Use Gunicorn with multiple workers:**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker
```

2. **Enable MongoDB indexing:**
```javascript
db.invoices.createIndex({ "invoiceNumber": 1 })
db.invoices.createIndex({ "uploadDate": -1 })
```

3. **Configure caching:**
- Use Redis for session management
- Cache API responses

### Frontend Optimization

1. **Enable production build:**
```bash
npm run build
```

2. **Use CDN for static assets**

3. **Enable gzip compression in Nginx**

---

## Security Checklist

- [ ] API keys stored in `.env` (not in code)
- [ ] `.env` added to `.gitignore`
- [ ] MongoDB authentication enabled
- [ ] CORS configured properly
- [ ] HTTPS enabled in production
- [ ] Rate limiting implemented
- [ ] Input validation active
- [ ] Regular security updates

---

## Monitoring & Logs

### Backend Logs

```bash
# View real-time logs
tail -f /var/log/fintel-api.log

# Check systemd logs
journalctl -u fintel-api -f
```

### MongoDB Logs

```bash
# View MongoDB logs
tail -f /var/log/mongodb/mongod.log
```

### Application Metrics

- Monitor API response times
- Track OCR accuracy
- Monitor anomaly detection rate
- Track system resource usage

---

## Backup & Recovery

### Database Backup

```bash
# Backup MongoDB
mongodump --db fintel_ai --out /backup/$(date +%Y%m%d)

# Restore MongoDB
mongorestore --db fintel_ai /backup/20241107/fintel_ai
```

### File Backup

```bash
# Backup uploads folder
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz AI-Agent/uploads/
```

---

## Support

For deployment issues:
- **GitHub Issues**: https://github.com/Parth703-wq/HackOps7/issues
- **Documentation**: See README.md
- **Email**: support@fintel-ai.com

---

**Happy Deploying! 🚀**
