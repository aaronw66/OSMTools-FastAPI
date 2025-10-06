from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ServerInfo(BaseModel):
    ip: str
    hostname: str
    label: str

class RestartRequest(BaseModel):
    servers: List[ServerInfo]
    service_name: Optional[str] = "image-recognition"
    restart_type: Optional[str] = "service"
    initiated_by: Optional[str] = "Unknown"  # Track who initiated the restart

class RestartResponse(BaseModel):
    status: str
    results: List[Dict[str, Any]]
    timestamp: str

class ServerStatusRequest(BaseModel):
    servers: List[ServerInfo]

class ServerStatusResponse(BaseModel):
    status: str
    servers: List[Dict[str, Any]]
    timestamp: str
