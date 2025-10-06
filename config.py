import os
from typing import Optional

class Settings:
    # Environment Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # SSH Configuration
    SSH_USERNAME: str = os.getenv("SSH_USERNAME", "ubuntu")
    SSH_KEY_PATH: str = os.getenv("SSH_KEY_PATH", "static/keys/image_identifier.pem")
    
    # File Paths
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    TYPE_DIR: str = os.getenv("TYPE_DIR", "type")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "6969"))
    
    # Ensure directories exist
    def __post_init__(self):
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.LOG_DIR, exist_ok=True)
        os.makedirs(self.TYPE_DIR, exist_ok=True)

settings = Settings()
settings.__post_init__()
