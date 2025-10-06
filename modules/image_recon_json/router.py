from fastapi import APIRouter, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import json

from .models import JsonGeneratorRequest, MachineTypeRequest, SendJsonRequest
from .service import ImageReconJsonService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
service = ImageReconJsonService()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page for Image Recon JSON tool"""
    try:
        return templates.TemplateResponse("image_recon_json.html", {"request": request})
    except Exception as e:
        # Fallback if template has issues
        from fastapi.responses import HTMLResponse
        return HTMLResponse(f"""
        <html>
        <head><title>Image Recon JSON Generator</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>📊 Image Recon JSON Generator</h1>
            <p>This tool is working! Template loading temporarily disabled.</p>
            <p><a href="/">← Back to Dashboard</a></p>
            <p><a href="/docs">View API Documentation</a></p>
            <hr>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)

@router.post("/generate-json")
async def generate_json(
    environment: str = Form(...),
    location: str = Form(...),
    channelID: str = Form(...),
    machineType: str = Form(...),
    poolType: Optional[int] = Form(0),
    screenType: Optional[str] = Form("DUAL"),
    streams_file: UploadFile = File(...)
):
    """Generate JSON configuration"""
    try:
        # Read uploaded file
        content = await streams_file.read()
        streams_content = content.decode('utf-8')
        
        # Prepare request data
        request_data = {
            'environment': environment,
            'location': location,
            'channelID': channelID,
            'machineType': machineType,
            'poolType': poolType,
            'screenType': screenType
        }
        
        # Generate JSON
        result = service.generate_json(request_data, streams_content)
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-machine-type")
async def add_machine_type(
    machineType: str = Form(...),
    gameType: int = Form(...)
):
    """Add a new machine type"""
    try:
        message = service.add_machine_type(machineType, gameType)
        return JSONResponse(content={"status": "success", "message": message})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/remove-machine-type")
async def remove_machine_type(
    machineType: str = Form(...)
):
    """Remove a machine type"""
    try:
        message = service.remove_machine_type(machineType)
        return JSONResponse(content={"status": "success", "message": message})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-machine-types")
async def get_machine_types():
    """Get list of machine types"""
    try:
        machine_types = service.load_machine_types()
        return JSONResponse(content=machine_types)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-channel-ids/{environment}")
async def get_channel_ids(environment: str):
    """Get all channel IDs for specific environment"""
    try:
        # Environment-specific Channel IDs
        channel_ids = {
            "qat": {
                "CP": "873",
                "WF": "888",
                "TBR": "890",
                "TBP": "891",
                "LAVIE": "892",
                "MDR": "894",
                "DHS": "895",
                "NWR": "897"
            },
            "uat": {
                "CP": "4186",
                "WF": "4187",
                "TBR": "4188",
                "TBP": "4189",
                "LAVIE": "4190",
                "MDR": "4191",
                "DHS": "4192",
                "NWR": "4196"
            },
            "prod": {
                "CP": "4171",
                "WF": "4172",
                "TBR": "4173",
                "TBP": "4174",
                "LAVIE": "4175",
                "MDR": "4178",
                "DHS": "4179",
                "NWR": "4182"
            }
        }
        
        env_channels = channel_ids.get(environment.lower(), channel_ids["prod"])
        return JSONResponse(content={"channel_ids": env_channels, "environment": environment})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-channel-id/{environment}/{location}")
async def get_channel_id(environment: str, location: str):
    """Get channel ID for specific environment and location"""
    try:
        # Environment-specific Channel IDs
        channel_ids = {
            "qat": {
                "CP": "873",
                "WF": "888",
                "TBR": "890",
                "TBP": "891",
                "LAVIE": "892",
                "MDR": "894",
                "DHS": "895",
                "NWR": "897"
            },
            "uat": {
                "CP": "4186",
                "WF": "4187",
                "TBR": "4188",
                "TBP": "4189",
                "LAVIE": "4190",
                "MDR": "4191",
                "DHS": "4192",
                "NWR": "4196"
            },
            "prod": {
                "CP": "4171",
                "WF": "4172",
                "TBR": "4173",
                "TBP": "4174",
                "LAVIE": "4175",
                "MDR": "4178",
                "DHS": "4179",
                "NWR": "4182"
            }
        }
        
        env_channels = channel_ids.get(environment.lower(), channel_ids["prod"])
        channel_id = env_channels.get(location.upper(), env_channels["CP"])
        return JSONResponse(content={"channel_id": channel_id, "environment": environment, "location": location})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-image-recon-json")
async def get_image_recon_json():
    """Get image-recon.json file content"""
    try:
        result = service.read_image_recon_json()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-servers-for-send")
async def get_servers_for_send():
    """Get list of servers for file sending"""
    try:
        servers = service.get_image_recon_servers()
        return JSONResponse(content={"status": "success", "servers": servers})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-json-to-servers")
async def send_json_to_servers(request: SendJsonRequest):
    """Send generated JSON to selected servers"""
    try:
        result = service.send_json_to_servers(
            request.json_content,
            [server.dict() for server in request.servers],
            request.remote_path
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
