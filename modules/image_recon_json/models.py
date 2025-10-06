from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class JsonGeneratorRequest(BaseModel):
    environment: str
    channelID: str
    machineType: str
    poolType: Optional[int] = 0
    screenType: Optional[str] = "DUAL"

class MachineTypeRequest(BaseModel):
    machineType: str
    gameType: int

class ServerInfo(BaseModel):
    ip: str
    hostname: str
    label: str

class SendJsonRequest(BaseModel):
    json_content: str
    servers: List[ServerInfo]
    remote_path: Optional[str] = "/usr/bin/OSMWatcher/list-new.json"

class JsonGeneratorResponse(BaseModel):
    status: str
    json_content: Optional[str] = None
    filename: Optional[str] = None
    message: Optional[str] = None

class SendJsonResponse(BaseModel):
    status: str
    results: List[Dict[str, Any]]
    timestamp: str
