from fastapi import APIRouter, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from .models import CCTVConfigRequest, CCTVBatchRequest
from .service import CCTVToolsService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
cctv_service = CCTVToolsService()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """CCTV Tools main page"""
    try:
        return templates.TemplateResponse("cctv_tools.html", {"request": request})
    except Exception as e:
        # Fallback if template has issues
        return HTMLResponse(f"""
        <html>
        <head><title>CCTV Tools</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>📹 CCTV Tools</h1>
            <p>Manage CCTV configurations and monitoring</p>
            <p><a href="/">← Back to Dashboard</a></p>
            <p><a href="/docs">View API Documentation</a></p>
            <hr>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)

@router.get("/status")
async def get_status():
    """Get CCTV system status"""
    try:
        result = cctv_service.get_cctv_status()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/configure")
async def configure_cctv(request: CCTVConfigRequest):
    """Configure CCTV system"""
    try:
        result = cctv_service.process_cctv_config(request.config_type, request.parameters)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/batch-operation")
async def batch_operation(request: CCTVBatchRequest):
    """Perform batch operations"""
    try:
        parameters = {
            "operation": request.operation,
            "targets": request.targets,
            "config": request.config or {}
        }
        result = cctv_service.process_cctv_config("batch_operation", parameters)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/upload-csv")
async def upload_csv(
    csv_file: UploadFile = File(...)
):
    """Upload and process CSV file"""
    try:
        content = await csv_file.read()
        csv_content = content.decode('utf-8')
        
        result = cctv_service.process_csv_upload(csv_content)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
