from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
from contextlib import asynccontextmanager
from config import settings

# Import routers
from modules.image_recon_json.router import router as image_recon_json_router
from modules.image_recon_service.router import router as image_recon_service_router
from modules.cctv_tools.router import router as cctv_tools_router
from modules.osmachine.router import router as osmachine_router
from modules.config_editor.router import router as config_editor_router

# Import service manager for background tasks
from modules.image_recon_service.service import ImageReconServiceManager

# Create a shared service manager instance for caching
shared_service_manager = ImageReconServiceManager()

# Background task for version caching
async def refresh_version_cache_periodically():
    """Background task to refresh version cache every 10 minutes"""
    global shared_service_manager
    
    while True:
        try:
            print("🔄 [Background] Starting periodic version cache refresh...")
            servers = shared_service_manager.get_image_recon_servers()
            
            if servers:
                # Pre-fetch all versions to populate cache
                for server in servers:
                    try:
                        version = shared_service_manager._get_server_version(server['ip'])
                        print(f"✅ [Background] Cached version for {server['hostname']}: {version}")
                    except Exception as e:
                        print(f"⚠️ [Background] Failed to cache version for {server['hostname']}: {e}")
                
                print(f"✅ [Background] Version cache refresh completed for {len(servers)} servers")
            else:
                print("⚠️ [Background] No servers found for version caching")
        except Exception as e:
            print(f"❌ [Background] Error in version cache refresh: {e}")
        
        # Wait 10 minutes before next refresh
        await asyncio.sleep(600)  # 600 seconds = 10 minutes

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup: Warm up cache immediately, then start background task
    print("🚀 Warming up version cache on startup...")
    global shared_service_manager
    try:
        servers = shared_service_manager.get_image_recon_servers()
        if servers:
            print(f"📊 Pre-caching versions for {len(servers)} servers...")
            for server in servers[:5]:  # Cache first 5 servers immediately for fast initial load
                try:
                    version = shared_service_manager._get_server_version(server['ip'])
                    print(f"✅ [Startup] Cached {server['hostname']}: {version}")
                except Exception as e:
                    print(f"⚠️ [Startup] Failed to cache {server['hostname']}: {e}")
            print("✅ Initial cache warm-up completed")
    except Exception as e:
        print(f"⚠️ Cache warm-up error: {e}")
    
    print("🔄 Starting background version cache refresh task (every 10 minutes)...")
    task = asyncio.create_task(refresh_version_cache_periodically())
    
    yield
    
    # Shutdown: Cancel background task
    print("🛑 Stopping background version cache refresh task...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("✅ Background task cancelled successfully")

# Create FastAPI app with lifespan
app = FastAPI(
    title="OSMTools v2.0",
    description="Operational Support Management Tools - Modernized with FastAPI",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/type", StaticFiles(directory="type"), name="type")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(image_recon_json_router, prefix="/image-recon-json", tags=["Image Recon JSON"])
app.include_router(image_recon_service_router, prefix="/image-recon-service", tags=["Image Recon Service"])
app.include_router(cctv_tools_router, prefix="/cctv-tools", tags=["CCTV Tools"])
app.include_router(osmachine_router, prefix="/osmachine", tags=["OSMachine"])
app.include_router(config_editor_router, prefix="/config-editor", tags=["Config Editor"])

@app.get("/")
async def home(request: Request):
    """Show dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard")
async def dashboard(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/api/system-stats")
async def get_system_stats():
    """Get system resource usage statistics"""
    import psutil
    
    # CPU usage (non-blocking, instant read)
    # This gets the CPU usage since the last call (instant)
    cpu_percent = psutil.cpu_percent(interval=0)
    
    # If it's 0.0 (first call), use a quick sample
    if cpu_percent == 0.0:
        cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # RAM usage
    ram = psutil.virtual_memory()
    ram_percent = ram.percent
    ram_used_gb = ram.used / (1024**3)
    ram_total_gb = ram.total / (1024**3)
    
    # Disk usage
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    disk_used_gb = disk.used / (1024**3)
    disk_total_gb = disk.total / (1024**3)
    
    return {
        "cpu": {
            "percent": round(cpu_percent, 1),
            "display": f"{cpu_percent:.1f}%"
        },
        "ram": {
            "percent": round(ram_percent, 1),
            "used_gb": round(ram_used_gb, 1),
            "total_gb": round(ram_total_gb, 1),
            "display": f"{ram_used_gb:.1f}GB / {ram_total_gb:.1f}GB"
        },
        "disk": {
            "percent": round(disk_percent, 1),
            "used_gb": round(disk_used_gb, 1),
            "total_gb": round(disk_total_gb, 1),
            "display": f"{disk_used_gb:.0f}GB / {disk_total_gb:.0f}GB"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True if settings.ENVIRONMENT == "development" else False
    )