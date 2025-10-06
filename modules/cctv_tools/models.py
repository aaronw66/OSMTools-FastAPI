from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class CCTVConfigRequest(BaseModel):
    config_type: str
    parameters: Dict[str, Any]

class CCTVBatchRequest(BaseModel):
    operation: str
    targets: List[str]
    config: Optional[Dict[str, Any]] = None

class CCTVResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class CCTVBatchResponse(BaseModel):
    status: str
    results: List[Dict[str, Any]]
    timestamp: str
