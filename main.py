from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(image_recon_json_router, prefix="/image-recon-json", tags=["Image Recon JSON"])
app.include_router(image_recon_service_router, prefix="/image-recon-service", tags=["Image Recon Service"])
app.include_router(cctv_tools_router, prefix="/cctv-tools", tags=["CCTV Tools"])
app.include_router(osmachine_router, prefix="/osmachine", tags=["OSMachine"])
app.include_router(config_editor_router, prefix="/config-editor", tags=["Config Editor"])

@app.get("/")
async def home():
    """Redirect to first tool"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/image-recon-json", status_code=302)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True if settings.ENVIRONMENT == "development" else False
    )