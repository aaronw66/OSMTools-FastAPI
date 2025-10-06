import os
import csv
import json
import logging
import hashlib
import re
import random
import time
import concurrent.futures as futures
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import tempfile

try:
    import requests
    from requests.auth import HTTPDigestAuth, HTTPBasicAuth
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from config import settings

class CCTVToolsService:
    def __init__(self):
        self.firmware_dir = settings.FIRMWARE_DIR
        self.results_dir = os.path.join(settings.LOG_DIR, 'cctv_results')
        
        # Ensure directories exist
        os.makedirs(self.firmware_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logger()
        
        # Load firmware versions from directory
        self.firmware_versions = self._load_firmware_versions()
    
    def _setup_logger(self):
        """Setup dedicated logger for CCTV tools"""
        logger = logging.getLogger('cctv_tools')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            log_file = os.path.join(settings.LOG_DIR, 'cctv_tools.log')
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] [CCTV-Tools] %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_firmware_versions(self) -> List[Dict]:
        """Load firmware versions from the firmware directory"""
        versions = []
        
        try:
            if not os.path.exists(self.firmware_dir):
                self.logger.warning(f"Firmware directory not found: {self.firmware_dir}")
                return []
            
            # List all .update files in the firmware directory
            for filename in sorted(os.listdir(self.firmware_dir)):
                if filename.endswith('.update'):
                    filepath = os.path.join(self.firmware_dir, filename)
                    
                    # Get file size
                    file_size = os.path.getsize(filepath)
                    size_mb = file_size / (1024 * 1024)
                    
                    # Extract date from filename (format: YYYYMMDD-...)
                    date_match = re.match(r'(\d{8})', filename)
                    date_str = 'Unknown'
                    if date_match:
                        date_raw = date_match.group(1)
                        try:
                            date_obj = datetime.strptime(date_raw, '%Y%m%d')
                            date_str = date_obj.strftime('%Y-%m-%d')
                        except ValueError:
                            pass
                    
                    # Extract version name from filename
                    version_name = filename.replace('.dingzhi.update', '').replace('.update', '')
                    
                    versions.append({
                        'name': version_name,
                        'file': filename,
                        'size': f'{size_mb:.1f} MB',
                        'date': date_str
                    })
            
            if not versions:
                self.logger.warning(f"No firmware files found in {self.firmware_dir}")
            else:
                self.logger.info(f"Loaded {len(versions)} firmware version(s)")
                
        except Exception as e:
            self.logger.error(f"Error loading firmware versions: {e}")
        
        return versions
    
    def get_firmware_versions(self) -> List[Dict]:
        """Get available firmware versions"""
        return self.firmware_versions
    
    def configure_devices(self, devices: List[Dict], firmware_version: str) -> Dict:
        """Configure multiple CCTV devices"""
        if not REQUESTS_AVAILABLE:
            return {"status": "error", "message": "Requests library not available"}
        
        self.logger.info(f"Starting configuration for {len(devices)} devices with firmware {firmware_version}")
        
        results = []
        
        # Use thread pool for concurrent operations
        with futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_device = {
                executor.submit(self._configure_single_device, device, firmware_version): device 
                for device in devices
            }
            
            for future in futures.as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    result['device'] = f"{device['room']} ({device['ip']})"
                    results.append(result)
                except Exception as e:
                    results.append({
                        'device': f"{device['room']} ({device['ip']})",
                        'ip': device['ip'],
                        'status': 'error',
                        'message': f'Configuration failed: {str(e)}',
                        'timestamp': datetime.now().isoformat()
                    })
        
        self.logger.info(f"Configuration completed. Success: {sum(1 for r in results if r['status'] == 'success')}, Failed: {sum(1 for r in results if r['status'] == 'error')}")
        
        return {
            "status": "success",
            "results": results,
            "summary": {
                "total": len(results),
                "success": sum(1 for r in results if r['status'] == 'success'),
                "failed": sum(1 for r in results if r['status'] == 'error')
            }
        }
    
    def _configure_single_device(self, device: Dict, firmware_version: str) -> Dict:
        """Configure a single CCTV device"""
        ip = device['ip']
        user = device.get('user', 'admin')
        user_sig = device.get('userSig', '')
        
        try:
            # Simulate device configuration (replace with actual API calls)
            time.sleep(random.uniform(0.5, 2.0))  # Simulate network delay
            
            # In real implementation, this would make HTTP requests to the device
            # Example: Configure device settings, upload firmware, etc.
            
            # For now, simulate success/failure based on IP pattern
            if self._simulate_device_response(ip):
                return {
                    'ip': ip,
                    'status': 'success',
                    'message': 'Device configured successfully',
                    'firmware': firmware_version,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'ip': ip,
                    'status': 'error',
                    'message': 'Device configuration failed - connection timeout',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'ip': ip,
                'status': 'error',
                'message': f'Configuration error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def update_firmware(self, devices: List[Dict], firmware_version: str) -> Dict:
        """Update firmware on multiple CCTV devices"""
        if not REQUESTS_AVAILABLE:
            return {"status": "error", "message": "Requests library not available"}
        
        self.logger.info(f"Starting firmware update for {len(devices)} devices to version {firmware_version}")
        
        results = []
        
        # Use thread pool for concurrent operations
        with futures.ThreadPoolExecutor(max_workers=3) as executor:  # Fewer threads for firmware updates
            future_to_device = {
                executor.submit(self._update_single_device, device, firmware_version): device 
                for device in devices
            }
            
            for future in futures.as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    result['device'] = f"{device['room']} ({device['ip']})"
                    results.append(result)
                except Exception as e:
                    results.append({
                        'device': f"{device['room']} ({device['ip']})",
                        'ip': device['ip'],
                        'status': 'error',
                        'message': f'Firmware update failed: {str(e)}',
                        'timestamp': datetime.now().isoformat()
                    })
        
        self.logger.info(f"Firmware update completed. Success: {sum(1 for r in results if r['status'] == 'success')}, Failed: {sum(1 for r in results if r['status'] == 'error')}")
        
        return {
            "status": "success",
            "results": results,
            "summary": {
                "total": len(results),
                "success": sum(1 for r in results if r['status'] == 'success'),
                "failed": sum(1 for r in results if r['status'] == 'error')
            }
        }
    
    def _update_single_device(self, device: Dict, firmware_version: str) -> Dict:
        """Update firmware on a single CCTV device"""
        ip = device['ip']
        
        try:
            # Simulate firmware update process
            time.sleep(random.uniform(2.0, 5.0))  # Firmware updates take longer
            
            # In real implementation, this would:
            # 1. Upload firmware file to device
            # 2. Trigger firmware update
            # 3. Wait for device to reboot
            # 4. Verify new firmware version
            
            if self._simulate_device_response(ip):
                return {
                    'ip': ip,
                    'status': 'success',
                    'message': f'Firmware updated to {firmware_version}',
                    'firmware': firmware_version,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'ip': ip,
                    'status': 'error',
                    'message': 'Firmware update failed - device not responding',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'ip': ip,
                'status': 'error',
                'message': f'Firmware update error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def check_device_status(self, devices: List[Dict]) -> Dict:
        """Check status of multiple CCTV devices"""
        if not REQUESTS_AVAILABLE:
            return {"status": "error", "message": "Requests library not available"}
        
        self.logger.info(f"Checking status for {len(devices)} devices")
        
        results = []
        
        # Use thread pool for concurrent status checks
        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_device = {
                executor.submit(self._check_single_device_status, device): device 
                for device in devices
            }
            
            for future in futures.as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    result['device'] = f"{device['room']} ({device['ip']})"
                    results.append(result)
                except Exception as e:
                    results.append({
                        'device': f"{device['room']} ({device['ip']})",
                        'ip': device['ip'],
                        'status': 'error',
                        'message': f'Status check failed: {str(e)}',
                        'timestamp': datetime.now().isoformat()
                    })
        
        return {
            "status": "success",
            "results": results,
            "summary": {
                "total": len(results),
                "online": sum(1 for r in results if r['status'] == 'success'),
                "offline": sum(1 for r in results if r['status'] == 'error')
            }
        }
    
    def _check_single_device_status(self, device: Dict) -> Dict:
        """Check status of a single CCTV device"""
        ip = device['ip']
        room = device.get('room', 'Unknown')
        user = device.get('user', 'admin')
        user_sig = device.get('userSig', '')
        
        try:
            # Try to connect to device API
            # Common CCTV device endpoints: /api/v1/device/info or /cgi-bin/api.cgi
            device_url = f"http://{ip}/api/v1/device/info"
            
            response = requests.get(
                device_url,
                auth=HTTPDigestAuth(user, user_sig) if user_sig else None,
                timeout=5
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Extract device information from response
                    firmware = data.get('firmware', data.get('version', data.get('buildDate', 'Unknown')))
                    device_name = data.get('deviceName', data.get('name', room))
                    app_id = data.get('appId', data.get('applicationId', '20008185'))
                    enable = data.get('enable', data.get('enabled', True))
                    
                    return {
                        'ip': ip,
                        'room': room,
                        'user': user,
                        'userSig': user_sig,
                        'status': 'success',
                        'message': 'Device online',
                        'firmware': firmware,
                        'build_date': firmware,  # Firmware version is the build date
                        'app_id': app_id,
                        'device_name': device_name,
                        'enable': enable,
                        'timestamp': datetime.now().isoformat()
                    }
                except json.JSONDecodeError:
                    # Device responded but not with JSON
                    return {
                        'ip': ip,
                        'room': room,
                        'user': user,
                        'userSig': user_sig,
                        'status': 'success',
                        'message': 'Device online',
                        'firmware': 'Unknown',
                        'build_date': 'Unknown',
                        'app_id': '20008185',
                        'device_name': room,
                        'enable': True,
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                return {
                    'ip': ip,
                    'room': room,
                    'user': user,
                    'userSig': user_sig,
                    'status': 'error',
                    'message': f'Device returned status code {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
                
        except requests.exceptions.Timeout:
            return {
                'ip': ip,
                'room': room,
                'user': user,
                'userSig': user_sig,
                'status': 'error',
                'message': 'Device timeout - not responding',
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.ConnectionError:
            return {
                'ip': ip,
                'room': room,
                'user': user,
                'userSig': user_sig,
                'status': 'error',
                'message': 'Device offline or not reachable',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'ip': ip,
                'room': room,
                'user': user,
                'userSig': user_sig,
                'status': 'error',
                'message': f'Error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def reboot_devices(self, devices: List[Dict]) -> Dict:
        """Reboot multiple CCTV devices"""
        if not REQUESTS_AVAILABLE:
            return {"status": "error", "message": "Requests library not available"}
        
        self.logger.info(f"Rebooting {len(devices)} devices")
        
        results = []
        
        # Use thread pool for concurrent reboots
        with futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_device = {
                executor.submit(self._reboot_single_device, device): device 
                for device in devices
            }
            
            for future in futures.as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    result = future.result()
                    result['device'] = f"{device['room']} ({device['ip']})"
                    results.append(result)
                except Exception as e:
                    results.append({
                        'device': f"{device['room']} ({device['ip']})",
                        'ip': device['ip'],
                        'status': 'error',
                        'message': f'Reboot failed: {str(e)}',
                        'timestamp': datetime.now().isoformat()
                    })
        
        self.logger.info(f"Reboot completed. Success: {sum(1 for r in results if r['status'] == 'success')}, Failed: {sum(1 for r in results if r['status'] == 'error')}")
        
        return {
            "status": "success",
            "results": results,
            "summary": {
                "total": len(results),
                "success": sum(1 for r in results if r['status'] == 'success'),
                "failed": sum(1 for r in results if r['status'] == 'error')
            }
        }
    
    def _reboot_single_device(self, device: Dict) -> Dict:
        """Reboot a single CCTV device"""
        ip = device['ip']
        
        try:
            # Simulate reboot process
            time.sleep(random.uniform(1.0, 3.0))
            
            # In real implementation, this would send reboot command to device
            
            if self._simulate_device_response(ip):
                return {
                    'ip': ip,
                    'status': 'success',
                    'message': 'Device rebooted successfully',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'ip': ip,
                    'status': 'error',
                    'message': 'Reboot command failed - device not responding',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'ip': ip,
                'status': 'error',
                'message': f'Reboot error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    
    def batch_operation(self, operation: str, devices: List[Dict], **kwargs) -> Dict:
        """Perform batch operation on devices"""
        if operation == 'configure':
            return self.configure_devices(devices, kwargs.get('firmware_version', ''))
        elif operation == 'update':
            return self.update_firmware(devices, kwargs.get('firmware_version', ''))
        elif operation == 'status':
            return self.check_device_status(devices)
        elif operation == 'reboot':
            return self.reboot_devices(devices)
        else:
            return {"status": "error", "message": f"Unknown operation: {operation}"}
    
    def save_results(self, operation: str, results: List[Dict]) -> str:
        """Save operation results to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cctv_{operation}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    'operation': operation,
                    'timestamp': datetime.now().isoformat(),
                    'results': results
                }, f, indent=2)
            
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return None