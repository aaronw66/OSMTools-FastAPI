from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Config Editor main page"""
    try:
        return templates.TemplateResponse("config_editor.html", {"request": request})
    except Exception as e:
        # Fallback if template has issues
        return HTMLResponse(f"""
        <html>
        <head><title>Config Editor</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
            <h1>⚙️ Config Editor</h1>
            <p>Edit JSON and XML configuration files</p>
            <p><a href="/">← Back to Dashboard</a></p>
            <p><a href="/docs">View API Documentation</a></p>
            <hr>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)

@router.get("/files")
async def list_config_files():
    """List available config files"""
    return JSONResponse(content={
        "status": "success",
        "files": [
            {"name": "config.json", "type": "json", "size": "2.4 KB"},
            {"name": "settings.xml", "type": "xml", "size": "1.8 KB"},
            {"name": "database.json", "type": "json", "size": "3.2 KB"}
        ]
    })
