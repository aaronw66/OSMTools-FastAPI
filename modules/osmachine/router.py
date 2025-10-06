from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """OSMachine main page"""
    try:
        return templates.TemplateResponse("osmachine.html", {"request": request})
    except Exception as e:
        # Fallback if template has issues
        return HTMLResponse(f"""
        <html>
        <head><title>OSMachine</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>🖥️ OSMachine</h1>
            <p>Machine restart and management operations</p>
            <p><a href="/">← Back to Dashboard</a></p>
            <p><a href="/docs">View API Documentation</a></p>
            <hr>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)

@router.get("/status")
async def get_machine_status():
    """Get machine status"""
    return JSONResponse(content={
        "status": "success",
        "data": {
            "machines": [
                {"name": "Server-01", "status": "online", "uptime": "5d 14h"},
                {"name": "Server-02", "status": "online", "uptime": "2d 8h"},
                {"name": "Server-03", "status": "maintenance", "uptime": "0h"}
            ]
        }
    })
