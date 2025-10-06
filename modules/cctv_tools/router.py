from fastapi import APIRouter, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import json

from .models import CCTVConfigRequest, CCTVBatchRequest
from .service import CCTVToolsService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
service = CCTVToolsService()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """CCTV Tools main page"""
    try:
        return templates.TemplateResponse("cctv_tools.html", {"request": request})
    except Exception as e:
        # Fallback if template has issues
        return HTMLResponse(f"""
        <html>
        <head><title>CCTV Batch Configuration Tool</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>📹 CCTV Batch Configuration Tool</h1>
            <p>Manage multiple CCTV devices with batch configuration and firmware updates.</p>
            <p><a href="/">← Back to Dashboard</a></p>
            <p><a href="/docs">View API Documentation</a></p>
            <hr>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)

@router.get("/get-firmware-versions")
async def get_firmware_versions():
    """Get available firmware versions"""
    try:
        versions = service.get_firmware_versions()
        return JSONResponse(content={"status": "success", "versions": versions})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/prepare-configuration")
async def prepare_configuration(request: Request):
    """Prepare configuration modal - show device list instantly without checking status"""
    try:
        data = await request.json()
        devices = data.get('devices', [])
        
        if not devices:
            return JSONResponse(content={"status": "error", "message": "No devices provided"})
        
        # Prepare device list for configuration modal (instant, no status check)
        results = []
        for device in devices:
            ip = device.get('ip', '')
            if not ip:
                continue
            
            # Extract device name from IP (last octet)
            device_name = ip.split('.')[-1] if '.' in ip else ip
            
            results.append({
                'ip': ip,
                'device_name': device_name,
                'room': device.get('room', ''),
                'user': device.get('user', ''),
                'user_sig': device.get('userSig', ''),
                'build_date': '',  # Will be populated during actual configuration
                'status': 'ONLINE',  # Assume online for modal display
            })
        
        return JSONResponse(content={
            'success': True,
            'results': results,
            'operation_type': 'Configuration',
            'total_devices': len(results),
            'message': f'Ready to configure {len(results)} devices'
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/configure-devices")
async def configure_devices(request: Request):
    """Configure multiple CCTV devices with TRTC settings"""
    try:
        data = await request.json()
        devices = data.get('devices', [])
        
        if not devices:
            return JSONResponse(content={"status": "error", "message": "No devices provided"})
        
        # Configuration doesn't need firmware version - it only needs Room/User/UserSig from CSV
        result = service.configure_devices(devices, '')
        
        # Save results
        if result.get('results'):
            service.save_results('configure', result['results'])
        
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/update-firmware")
async def update_firmware(request: Request):
    """Update firmware on multiple CCTV devices"""
    try:
        data = await request.json()
        devices = data.get('devices', [])
        firmware_version = data.get('firmware_version', '')
        
        if not devices:
            return JSONResponse(content={"status": "error", "message": "No devices provided"})
        
        if not firmware_version:
            return JSONResponse(content={"status": "error", "message": "Firmware version is required"})
        
        result = service.update_firmware(devices, firmware_version)
        
        # Save results
        if result.get('results'):
            service.save_results('update', result['results'])
        
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/check-status")
async def check_status(request: Request):
    """Check status of multiple CCTV devices"""
    try:
        data = await request.json()
        devices = data.get('devices', [])
        
        if not devices:
            return JSONResponse(content={"status": "error", "message": "No devices provided"})
        
        result = service.check_device_status(devices)
        
        # Save results
        if result.get('results'):
            service.save_results('status', result['results'])
        
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/reboot-devices")
async def reboot_devices(request: Request):
    """Reboot multiple CCTV devices"""
    try:
        data = await request.json()
        devices = data.get('devices', [])
        
        if not devices:
            return JSONResponse(content={"status": "error", "message": "No devices provided"})
        
        result = service.reboot_devices(devices)
        
        # Save results
        if result.get('results'):
            service.save_results('reboot', result['results'])
        
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/batch-operation")
async def batch_operation(request: CCTVBatchRequest):
    """Perform batch operation on CCTV devices"""
    try:
        result = service.batch_operation(
            request.operation,
            [device.dict() for device in request.devices],
            firmware_version=request.firmware_version
        )
        
        # Save results
        if result.get('results'):
            service.save_results(request.operation, result['results'])
        
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/upload-csv")
async def upload_csv(csv_file: UploadFile = File(...)):
    """Upload and parse CSV file containing device information"""
    try:
        if not csv_file.filename.endswith('.csv'):
            return JSONResponse(content={"status": "error", "message": "File must be a CSV"})
        
        # Read CSV content
        content = await csv_file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV
        devices = []
        lines = csv_content.strip().split('\n')
        
        # Skip header row and parse data
        for i, line in enumerate(lines[1:], 1):
            if line.strip():
                columns = [col.strip() for col in line.split(',')]
                if len(columns) >= 4:
                    devices.append({
                        'ip': columns[0],
                        'room': columns[1],
                        'user': columns[2],
                        'userSig': columns[3]
                    })
                else:
                    return JSONResponse(content={
                        "status": "error", 
                        "message": f"Invalid CSV format at line {i+1}. Expected: IP,Room,User,UserSig"
                    })
        
        if not devices:
            return JSONResponse(content={"status": "error", "message": "No valid devices found in CSV"})
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Successfully parsed {len(devices)} devices",
            "devices": devices
        })
        
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Error processing CSV: {str(e)}"}, status_code=500)

@router.get("/download-sample-csv")
async def download_sample_csv():
    """Download sample CSV file"""
    try:
        from fastapi.responses import Response
        
        sample_csv = """IP,Room,User,UserSig
192.168.1.100,Room01,user1,signature1
192.168.1.101,Room02,user2,signature2
192.168.1.102,Room03,user3,signature3"""
        
        return Response(
            content=sample_csv,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sample_cctv.csv"}
        )
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.get("/get-operation-results/{operation}")
async def get_operation_results(operation: str):
    """Get results of a specific operation"""
    try:
        # This would typically load results from database or files
        # For now, return empty results
        return JSONResponse(content={
            "status": "success",
            "operation": operation,
            "results": []
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)