#!/usr/bin/env python3
"""
OSMTools v2.0 - Simple Startup Script
"""

def main():
    print("🚀 Starting OSMTools v2.0...")
    
    try:
        # Check if FastAPI is installed
        import fastapi
        import uvicorn
        print("✅ FastAPI is available")
    except ImportError:
        print("❌ FastAPI not installed. Installing now...")
        import subprocess
        import sys
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "fastapi", "uvicorn[standard]", "jinja2", "python-multipart",
            "--break-system-packages"
        ])
        print("✅ FastAPI installed successfully")
    
    # Import and run the app
    from main import app
    
    print("\n🎉 OSMTools v2.0 is starting!")
    print("📍 Dashboard: http://localhost:6969")
    print("📍 API Docs: http://localhost:6969/docs")
    print("🛑 Press Ctrl+C to stop\n")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=6969,
        log_level="info"
    )

if __name__ == "__main__":
    main()
