from fastapi import APIRouter, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import json

from .models import RestartRequest, ServerStatusRequest
from .service import ImageReconServiceManager

router = APIRouter()
templates = Jinja2Templates(directory="templates")
service_manager = ImageReconServiceManager()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Image Recon Service main page"""
    try:
        return templates.TemplateResponse("image_recon_service.html", {"request": request})
    except Exception as e:
        # Fallback if template has issues
        return HTMLResponse(f"""
        <html>
        <head><title>Image Recon Service Manager</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>🔄 Image Recon Service Manager</h1>
            <p>Restart and manage image recognition services</p>
            <p><a href="/">← Back to Dashboard</a></p>
            <p><a href="/docs">View API Documentation</a></p>
            <hr>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)

@router.get("/get-servers")
async def get_servers():
    """Get list of servers for service management"""
    try:
        servers = service_manager.get_image_recon_servers()
        return JSONResponse(content={"status": "success", "servers": servers})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.get("/get-all-server-versions")
async def get_all_server_versions():
    """Get current versions for all servers - matches Flask endpoint"""
    try:
        servers = service_manager.get_image_recon_servers()
        version_results = []
        
        for server in servers:
            ip = server['ip']
            hostname = server['hostname']
            
            try:
                version = service_manager._get_server_version(ip)
                version_results.append({
                    'ip': ip,
                    'hostname': hostname,
                    'version': version,
                    'success': version != "Unknown"
                })
            except Exception as e:
                version_results.append({
                    'ip': ip,
                    'hostname': hostname,
                    'version': 'Error',
                    'success': False,
                    'error': str(e)
                })
        
        return JSONResponse(content={
            "status": "success",
            "results": version_results
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/restart-service")
async def restart_service(restart_req: RestartRequest, request: Request):
    """Restart service on selected servers"""
    try:
        # Get client IP for logging (use initiated_by from request, or fallback to client IP)
        client_ip = request.client.host if request.client else "Unknown"
        initiated_by = restart_req.initiated_by or client_ip
        
        result = service_manager.restart_service(
            [server.dict() for server in restart_req.servers],
            restart_req.service_name,
            initiated_by
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/check-status")
async def check_status(request: ServerStatusRequest):
    """Check service status on selected servers"""
    try:
        result = service_manager.check_service_status(
            [server.dict() for server in request.servers]
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/restart-machine")
async def restart_machine(request: RestartRequest):
    """Restart entire machine on selected servers"""
    try:
        result = service_manager.restart_machine(
            [server.dict() for server in request.servers]
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

# =====================
# 🔍 Additional Functionality from Original restart_ir.py
# =====================

@router.post("/search-machines")
async def search_machines(request: Request):
    """Search for machines by hostname, IP, or label"""
    try:
        data = await request.json()
        query = data.get('query', '').strip()
        
        if not query or len(query) < 2:
            return JSONResponse(content={"status": "error", "message": "Query must be at least 2 characters"})
        
        results = service_manager.search_machines(query)
        return JSONResponse(content={"status": "success", "results": results})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/get-logs")
async def get_logs(request: Request):
    """Get logs from a specific server - matches Flask version"""
    try:
        data = await request.json()
        server_ip = data.get('server_ip')
        lines = data.get('lines', 100)  # Match Flask default
        
        if not server_ip:
            return JSONResponse(content={"status": "error", "message": "Server IP is required"}, status_code=400)
        
        logs = service_manager._get_logs_from_server(server_ip, lines)
        
        if "Error:" in logs:
            return JSONResponse(content={"status": "error", "message": logs}, status_code=500)
        
        return JSONResponse(content={"status": "success", "logs": logs})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/refresh-servers")
async def refresh_servers():
    """Refresh server list by fetching IDs from each server - matches Flask version"""
    try:
        result = service_manager.refresh_servers()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.get("/get-email-settings")
async def get_email_settings():
    """Get current email configuration"""
    try:
        config = service_manager.load_email_config()
        return JSONResponse(content={"status": "success", "config": config})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/send-batch-email")
async def send_batch_email(request: Request):
    """Send batch email notification"""
    try:
        data = await request.json()
        recipients = data.get('recipients', [])
        subject = data.get('subject', 'Image Recon Service Notification')
        message = data.get('message', '')
        results = data.get('results', [])
        
        if not recipients:
            config = service_manager.load_email_config()
            recipients = config.get('recipients', [])
        
        result = service_manager.send_batch_email(recipients, subject, message, results)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)
