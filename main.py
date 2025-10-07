from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from config import settings

# Import routers
from modules.image_recon_json.router import router as image_recon_json_router
from modules.image_recon_service.router import router as image_recon_service_router
from modules.cctv_tools.router import router as cctv_tools_router
from modules.osmachine.router import router as osmachine_router
from modules.config_editor.router import router as config_editor_router

# Create FastAPI app
app = FastAPI(
    title="OSMTools v2.0",
    description="Operational Support Management Tools - Modernized with FastAPI",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    
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