# 🚀 Quick Start Guide - OSMTools v2.0

## Start Your FastAPI Server

### Method 1: Using the Startup Script (Recommended)
```bash
cd /Users/aaronwong/Downloads/OSMTools-master
python3 start_server.py
```

### Method 2: Using uvicorn directly
```bash
cd /Users/aaronwong/Downloads/OSMTools-master
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Method 3: Using Python directly
```bash
cd /Users/aaronwong/Downloads/OSMTools-master
python3 main.py
```

## 📍 Access Your Application

Once the server starts, you can access:

- **🏠 Main API**: http://localhost:8000
- **📊 Dashboard**: http://localhost:8000 (beautiful new dashboard)
- **🔍 Health Check**: http://localhost:8000/health
- **📚 API Documentation**: http://localhost:8000/docs
- **📖 Alternative Docs**: http://localhost:8000/redoc

## 🧪 Test the Image Recon JSON Tool

1. Go to http://localhost:8000
2. Click on "Image Recon JSON" card
3. Try uploading a CSV file and generating JSON
4. See the beautiful new interface with separated HTML, CSS, and JS!

## 🛑 Stop the Server

Press `Ctrl+C` in the terminal where the server is running.

## 🐛 Troubleshooting

### If you get import errors:
```bash
pip install fastapi uvicorn jinja2 python-multipart --break-system-packages
```

### If port 8000 is busy:
Change the port in the startup command:
```bash
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### If templates don't load:
Make sure you're in the correct directory:
```bash
cd /Users/aaronwong/Downloads/OSMTools-master
ls -la templates/  # Should show dashboard.html and other files
```

## 🎉 What You'll See

1. **Modern Dashboard**: Beautiful gradient design with tool cards
2. **Separated Architecture**: Clean HTML, CSS, and JS files
3. **FastAPI Features**: Automatic API documentation
4. **Responsive Design**: Works on desktop and mobile
5. **Professional UI**: Smooth animations and modern styling

## 📝 Next Steps

Once you confirm the server is working:
1. Test the Image Recon JSON functionality
2. We can migrate the remaining modules:
   - Image Recon Service (Restart IR)
   - CCTV Tools
   - OSMachine (Machine Restart)
   - Config Editor (Box Editor)

Enjoy your modernized OSMTools! 🎊
