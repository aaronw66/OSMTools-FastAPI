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
    from requests.auth import HTTPDigestAuth, HTTPBasicAuth, AuthBase
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from config import settings


class RobustDigestAuth(AuthBase):
    """Robust Digest Authentication that handles various header formats"""
    
    def __init__(self, username, password):
        self.username = username
        self.password = password
        
    def __call__(self, r):
        r.register_hook('response', self._handle_401)
        return r
    
    def _handle_401(self, response, **kwargs):
        if response.status_code == 401:
            auth_header = response.headers.get('WWW-Authenticate', '')
            if 'Digest' in auth_header:
                try:
                    challenge = self._parse_challenge_robust(auth_header)
                    if challenge:
                        auth_value = self._build_standard_digest_header(response.request, challenge)
                        new_request = response.request.copy()
                        new_request.headers['Authorization'] = auth_value
                        new_response = response.connection.send(new_request, **kwargs)
                        new_response.history.append(response)
                        return new_response
                except Exception as e:
                    pass
        return response
    
    def _parse_challenge_robust(self, auth_header):
        try:
            challenge_str = auth_header.replace('Digest ', '', 1)
            challenge = {}
            parts = re.findall(r'(\w+)=(?:"([^"]*)"|([^,\s]+))', challenge_str)
            for key, quoted_val, unquoted_val in parts:
                challenge[key] = quoted_val or unquoted_val
            
            required_fields = ['realm', 'nonce']
            for field in required_fields:
                if field not in challenge:
                    return None
            return challenge
        except Exception:
            return None
    
    def _build_standard_digest_header(self, request, challenge):
        realm = challenge.get('realm', '')
        nonce = challenge.get('nonce', '')
        qop = challenge.get('qop', '')
        opaque = challenge.get('opaque', '')
        algorithm = challenge.get('algorithm', 'MD5')
        
        cnonce = hashlib.md5(f"{random.random()}:{time.time()}".encode()).hexdigest()[:8]
        uri = request.path_url
        method = request.method
        
        ha1 = hashlib.md5(f"{self.username}:{realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        
        if qop and 'auth' in qop:
            nc = "00000001"
            response_hash = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()).hexdigest()
            auth_header = f'Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="{uri}", algorithm="{algorithm}", response="{response_hash}", qop="{qop}", nc={nc}, cnonce="{cnonce}"'
            if opaque:
                auth_header += f', opaque="{opaque}"'
        else:
            response_hash = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            auth_header = f'Digest username="{self.username}", realm="{realm}", nonce="{nonce}", uri="{uri}", algorithm="{algorithm}", response="{response_hash}"'
            if opaque:
                auth_header += f', opaque="{opaque}"'
        
        return auth_header


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
        """Check status of a single CCTV device - matches original Flask implementation"""
        ip = device['ip']
        room = device.get('room', 'Unknown')
        username = device.get('user', 'admin')
        password = device.get('userSig', '123456')
        
        result = {
            'ip': ip,
            'room': room,
            'user': username,
            'userSig': password,
            'status': 'error',
            'message': 'Device offline',
            'device_name': 'Unknown',
            'build_date': 'Unknown',
            'app_id': '20008185',
            'enable': True,  # Default to True if we can't determine (like old version)
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Step 1: Check if device is reachable (TCP connection test instead of ping)
            import socket
            
            try:
                # Try to connect to port 80 (HTTP) with a short timeout
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((ip, 80))
                sock.close()
            except (socket.timeout, socket.error, OSError) as e:
                result['message'] = f'Device offline - connection failed: {str(e)}'
                return result
            
            # Step 2: Get device info from /digest/frmGetFactoryInfo
            device_info_url = f"http://{ip}/digest/frmGetFactoryInfo"
            device_info_payload = {"Type": 0, "Dev": 1, "Ch": 1, "Data": {}}
            
            try:
                # Try multiple auth methods
                auth_methods = [
                    ("RobustDigest", RobustDigestAuth(username, password)),
                    ("StandardDigest", HTTPDigestAuth(username, password)),
                    ("BasicAuth", HTTPBasicAuth(username, password)),
                    ("NoAuth", None)
                ]
                
                response = None
                for auth_name, auth in auth_methods:
                    try:
                        response = requests.post(
                            device_info_url,
                            json=device_info_payload,
                            auth=auth,
                            timeout=5
                        )
                        if response.status_code == 200:
                            self.logger.info(f"[{ip}] Device info retrieved using {auth_name}")
                            break
                    except Exception:
                        continue
                
                if response and response.status_code == 200:
                    data = response.json().get('Data', {})
                    result['device_name'] = data.get('DeviceName', 'Unknown')
                    result['build_date'] = data.get('BuildDate', 'Unknown')
            except Exception as e:
                self.logger.warning(f"[{ip}] Could not get device info: {e}")
            
            # Step 3: Get TRTC config from /digest/frmTrtcConfig
            trtc_config_url = f"http://{ip}/digest/frmTrtcConfig"
            
            try:
                # Try multiple auth methods like the original Flask code
                auth_methods = [
                    ("RobustDigest", RobustDigestAuth(username, password)),
                    ("StandardDigest", HTTPDigestAuth(username, password)),
                    ("BasicAuth", HTTPBasicAuth(username, password)),
                    ("NoAuth", None)
                ]
                
                response = None
                last_error = None
                for auth_name, auth in auth_methods:
                    try:
                        response = requests.get(trtc_config_url, auth=auth, timeout=5)
                        if response.status_code == 200:
                            self.logger.info(f"[{ip}] TRTC config retrieved using {auth_name}")
                            break
                        else:
                            last_error = f"{auth_name} returned {response.status_code}"
                    except Exception as e:
                        last_error = f"{auth_name} failed: {str(e)}"
                        continue
                
                if not response or response.status_code != 200:
                    raise Exception(f"All auth methods failed. Last: {last_error}")
                
                if response.status_code == 200:
                    data = response.json().get('Data', {})
                    result['enable'] = data.get('Enable', 0) == 1
                    result['app_id'] = str(data.get('AppId', '20008185'))
                    # Only update if TRTC has values, otherwise keep CSV values
                    trtc_room = data.get('Room', '')
                    trtc_user = data.get('User', '')
                    trtc_sig = data.get('UserSig', '')
                    if trtc_room:
                        result['room'] = trtc_room
                    if trtc_user:
                        result['user'] = trtc_user
                    if trtc_sig:
                        result['userSig'] = trtc_sig
            except Exception as e:
                self.logger.warning(f"[{ip}] Could not get TRTC config: {e}")
            
            # If we got here, device is online
            result['status'] = 'success'
            result['message'] = 'Device online'
            
        except Exception as e:
            result['message'] = f'Error: {str(e)}'
            self.logger.error(f"[{ip}] Status check error: {e}")
        
        return result
    
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