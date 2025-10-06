import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_image_recon_logger():
    """Set up dedicated logger for Image Recon Service"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "image_recon_service.log")
    
    # Create logger
    logger = logging.getLogger('image_recon_service')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create rotating file handler (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024, 
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [Image-Recon] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    logger.info("=" * 80)
    logger.info("🚀 Image Recon Service logger initialized")
    logger.info("=" * 80)
    
    return logger

# Initialize logger
logger = setup_image_recon_logger()

