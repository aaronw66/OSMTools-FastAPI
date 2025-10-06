from pydantic import BaseModel
from typing import List, Optional

class CCTVDevice(BaseModel):
    ip: str
    room: str
    user: str
    userSig: str

class CCTVConfigRequest(BaseModel):
    devices: List[CCTVDevice]
    firmware_version: str
    operation_type: Optional[str] = "configure"

class CCTVBatchRequest(BaseModel):
    operation: str  # configure, update, status, reboot
    devices: List[CCTVDevice]
    firmware_version: Optional[str] = None

class CCTVStatusRequest(BaseModel):
    devices: List[CCTVDevice]

class CCTVRebootRequest(BaseModel):
    devices: List[CCTVDevice]

class FirmwareVersion(BaseModel):
    name: str
    file: str
    size: Optional[str] = None
    date: Optional[str] = None

class OperationResult(BaseModel):
    device: str
    ip: str
    status: str  # success, error, warning
    message: str
    timestamp: str
    firmware: Optional[str] = None
    uptime: Optional[str] = None