import json
import csv
import os
from typing import Dict, List, Any
from datetime import datetime
from config import settings

class CCTVToolsService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def process_cctv_config(self, config_type: str, parameters: Dict[str, Any]) -> Dict:
        """Process CCTV configuration based on type"""
        try:
            if config_type == "camera_setup":
                return self._setup_cameras(parameters)
            elif config_type == "monitoring_config":
                return self._configure_monitoring(parameters)
            elif config_type == "batch_operation":
                return self._batch_operation(parameters)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown configuration type: {config_type}"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _setup_cameras(self, parameters: Dict[str, Any]) -> Dict:
        """Setup camera configurations"""
        camera_count = parameters.get('camera_count', 1)
        resolution = parameters.get('resolution', '1920x1080')
        fps = parameters.get('fps', 30)
        
        cameras = []
        for i in range(camera_count):
            camera = {
                "id": f"camera_{i+1:03d}",
                "name": f"Camera {i+1}",
                "resolution": resolution,
                "fps": fps,
                "status": "configured",
                "stream_url": f"rtmp://localhost/live/camera_{i+1:03d}"
            }
            cameras.append(camera)
        
        return {
            "status": "success",
            "message": f"Configured {camera_count} cameras",
            "data": {
                "cameras": cameras,
                "total_count": camera_count
            }
        }
    
    def _configure_monitoring(self, parameters: Dict[str, Any]) -> Dict:
        """Configure monitoring settings"""
        monitoring_type = parameters.get('type', 'basic')
        interval = parameters.get('interval', 60)
        alerts_enabled = parameters.get('alerts', True)
        
        config = {
            "monitoring_type": monitoring_type,
            "check_interval": interval,
            "alerts_enabled": alerts_enabled,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        return {
            "status": "success",
            "message": "Monitoring configuration updated",
            "data": config
        }
    
    def _batch_operation(self, parameters: Dict[str, Any]) -> Dict:
        """Perform batch operations on CCTV systems"""
        operation = parameters.get('operation', 'status_check')
        targets = parameters.get('targets', [])
        
        results = []
        for target in targets:
            result = {
                "target": target,
                "operation": operation,
                "status": "success",
                "message": f"Operation '{operation}' completed on {target}",
                "timestamp": datetime.now().isoformat()
            }
            results.append(result)
        
        return {
            "status": "success",
            "message": f"Batch operation '{operation}' completed on {len(targets)} targets",
            "data": {
                "results": results,
                "summary": {
                    "total": len(targets),
                    "successful": len(targets),
                    "failed": 0
                }
            }
        }
    
    def process_csv_upload(self, csv_content: str) -> Dict:
        """Process uploaded CSV file for CCTV configuration"""
        try:
            # Parse CSV content
            csv_reader = csv.DictReader(csv_content.splitlines())
            rows = list(csv_reader)
            
            processed_items = []
            for row in rows:
                processed_item = {
                    "id": row.get('id', ''),
                    "name": row.get('name', ''),
                    "ip": row.get('ip', ''),
                    "status": "processed",
                    "timestamp": datetime.now().isoformat()
                }
                processed_items.append(processed_item)
            
            return {
                "status": "success",
                "message": f"Processed {len(processed_items)} items from CSV",
                "data": {
                    "items": processed_items,
                    "count": len(processed_items)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process CSV: {str(e)}"
            }
    
    def get_cctv_status(self) -> Dict:
        """Get current CCTV system status"""
        return {
            "status": "success",
            "data": {
                "system_status": "operational",
                "active_cameras": 12,
                "total_cameras": 15,
                "alerts": 2,
                "last_update": datetime.now().isoformat(),
                "uptime": "5 days, 14 hours",
                "storage_usage": "68%"
            }
        }
