import json
import os
import csv
import re
import tempfile
import logging
from typing import Dict, List, Tuple
from datetime import datetime
try:
    import paramiko
    from scp import SCPClient
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False
from config import settings

# Setup logger
logger = logging.getLogger(__name__)

class ImageReconJsonService:
    def __init__(self):
        self.type_dir = settings.TYPE_DIR
        self.machine_types_file = os.path.join(self.type_dir, 'machine_types.json')
        self.game_types_file = os.path.join(self.type_dir, 'game_types.json')
        
        # Ensure type directory exists
        os.makedirs(self.type_dir, exist_ok=True)
    
    def load_machine_types(self) -> Dict:
        """Load machine types from JSON file"""
        if os.path.exists(self.machine_types_file):
            try:
                with open(self.machine_types_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def load_game_types(self) -> Dict:
        """Load game types from JSON file"""
        if os.path.exists(self.game_types_file):
            try:
                with open(self.game_types_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def save_machine_types(self, machine_types: Dict) -> None:
        """Save machine types to JSON file"""
        with open(self.machine_types_file, 'w') as f:
            json.dump(machine_types, f, indent=4)
    
    def save_game_types(self, game_types: Dict) -> None:
        """Save game types to JSON file"""
        with open(self.game_types_file, 'w') as f:
            json.dump(game_types, f, indent=4)
    
    def add_machine_type(self, machine_type: str, game_type: int) -> str:
        """Add a new machine type"""
        machine_types = self.load_machine_types()
        game_types = self.load_game_types()
        
        machine_types[machine_type] = True
        game_types[machine_type] = game_type
        
        self.save_machine_types(machine_types)
        self.save_game_types(game_types)
        
        return "Machine type added successfully!"
    
    def remove_machine_type(self, machine_type: str) -> str:
        """Remove a machine type"""
        machine_types = self.load_machine_types()
        game_types = self.load_game_types()
        
        if machine_type in machine_types:
            del machine_types[machine_type]
            if machine_type in game_types:
                del game_types[machine_type]
            
            self.save_machine_types(machine_types)
            self.save_game_types(game_types)
            
            return f"Machine type {machine_type} removed successfully."
        else:
            return f"Machine type {machine_type} not found."
    
    def generate_json(self, request_data: Dict, streams_content: str) -> Dict:
        """Generate JSON configuration"""
        environment = request_data['environment']
        machine_type = request_data['machineType']
        pool_type = int(request_data.get('poolType', 0)) if request_data.get('poolType') is not None else 0
        screen_type = request_data.get('screenType', 'DUAL')
        
        logger.info(f"🔧 Generating JSON: machine_type={machine_type}, pool_type={pool_type} (type: {type(pool_type)})")
        
        # Environment-specific URLs
        urls = {
            "qat": "http://10.19.131.168:18087/gm/onstreamgmstatechange",
            "uat": "http://10.0.132.123:18087/gm/onstreamgmstatechange",
            "prod": "http://10.85.140.219:18087/gm/onstreamgmstatechange"
        }
        
        # Environment-specific Channel IDs
        channel_ids = {
            "qat": {
                "CP": "873",
                "WF": "888",
                "TBR": "890",
                "TBP": "891",
                "LAVIE": "892",
                "MDR": "894",
                "DHS": "895",
                "NWR": "897"
            },
            "uat": {
                "CP": "4186",
                "WF": "4187",
                "TBR": "4188",
                "TBP": "4189",
                "LAVIE": "4190",
                "MDR": "4191",
                "DHS": "4192",
                "NWR": "4196"
            },
            "prod": {
                "CP": "4171",
                "WF": "4172",
                "TBR": "4173",
                "TBP": "4174",
                "LAVIE": "4175",
                "MDR": "4178",
                "DHS": "4179",
                "NWR": "4182"
            }
        }
        
        account_urls = {
            "qat": "http://10.19.131.168:18087/gm/getgm_info",
            "uat": "http://10.0.132.123:18087/gm/getgm_info",
            "prod": "http://10.85.140.219:18087/gm/getgm_info"
        }
        
        buckets = {
            "qat": "public-file-browser-files-06b4dbdb02d7",
            "uat": "public-file-browser-files-06b4dbdb02d7",
            "prod": "public-file-browser-files-02cca558e6ed"
        }
        
        selected_url = urls.get(environment, urls["prod"])
        selected_account_url = account_urls.get(environment, account_urls["prod"])
        selected_bucket = buckets.get(environment, buckets["prod"])
        
        # Get environment-specific channel ID (default to CP location)
        location = request_data.get('location', 'CP')
        env_channels = channel_ids.get(environment, channel_ids["prod"])
        channel_id = env_channels.get(location, env_channels["CP"])
        
        # Base JSON structure
        json_data = {
            "send": True,
            "log": True,
            "url": selected_url,
            "accountUrl": selected_account_url,
            "UserSig": "eJyrVgrxCdYrSy1SslIy0jNQ0gHzM1NS80oy0zLBwvnFuVDh4pTsxIKCzBQlKyMDAwMLQwtTiHhqRUFmUaqSlaGpqSlIBiJakpkLEjM3sTA0NTE3sICakZkONLOgMC8nrcSoKK3IxD83Kdm4yiDTzMkkIj8twNvfMiKnOKiowtsxKdUtOMfXVqkWAH43MQ0_",
            "UserId": "osm",
            "ossBasePathBowl": "bowl",
            "ossBasePathStream": "pc-snapshot",
            "ossEndpoint": "oss-ap-southeast-1.aliyuncs.com",
            "ossAccessKeyId": "LTAI5tML8MpgVh65bsSj9Eag",
            "ossAccessKeySecret": "XYg6vxNJeUqyej4WQQ5J0asBo44H3W",
            "ossBucket": "liveslots-prod-snapshot",
            "bucket": selected_bucket,
            "pool": []
        }
        
        # Process CSV data
        game_types = self.load_game_types()
        stream_data = csv.reader(streams_content.splitlines())
        streams = [row for row in list(stream_data)[1:] if len(row) >= 1 and row[0].strip() != '']
        
        # Group streams by gametype
        pool_dict = {}
        
        for stream in streams:
            if len(stream) < 1:
                continue
            
            stream_id = stream[0]
            game_type_str = str(stream[3]) if len(stream) > 3 and stream[3].strip() else str(game_types.get(machine_type, 0))
            game_type = int(game_type_str) if game_type_str.isdigit() and 0 <= int(game_type_str) <= 99 else game_types.get(machine_type, 1)
            
            if game_type not in pool_dict:
                pool_dict[game_type] = []
            
            pool_dict[game_type].append(stream)
        
        # Generate pools
        for game_type, pool_streams in pool_dict.items():
            for i in range(0, len(pool_streams), 5):
                pool_streams_chunk = pool_streams[i:i+5]
                
                # Determine suffixes based on screen type
                if screen_type == "SINGLE":
                    src_suffix = "_MAIN"
                    src1_suffix = "_MAIN"
                    bowl_suffix = "_MAIN"
                else:
                    src_suffix = "_POOL"
                    src1_suffix = "_MAIN"
                    bowl_suffix = "_POOL"
                
                pool_entry = {
                    "channel": f"channel{channel_id}",
                    "src": f"rtmp://srs-pull.prod.sn-game.net/live/{pool_streams_chunk[0][0]}{src_suffix}",
                    "gametype": game_type,
                    "skipT": 20,
                    "sleepT": 333,
                    "jackpotId": "0",
                    "poolType": pool_type,
                    "gamelist": []
                }
                
                logger.info(f"✅ Added poolType={pool_type} to pool entry")
                
                for stream in pool_streams_chunk:
                    stream_id = stream[0]
                    stream_num = re.findall(r'\d+', stream_id)
                    padded_id = stream_num[0].zfill(4) if stream_num else "0000"
                    
                    new_entry = {
                        "id": f"{channel_id}-{machine_type}-{padded_id}",
                        "src": f"rtmp://srs-pull.prod.sn-game.net/live/{stream_id}{src1_suffix}",
                        "bowl": f"rtmp://srs-pull.prod.sn-game.net/live/{stream_id}{bowl_suffix}",
                        "subtype": 0,
                        "skipT": 20,
                        "sleepT": 333,
                        "roomId": f"{stream_id}{src1_suffix}",
                        "sId": f"{stream_id}"
                    }
                    
                    if src_suffix == "_MAIN":
                        new_entry["poolSrc"] = ""
                    else:
                        new_entry["poolSrc"] = f"rtmp://srs-pull.prod.sn-game.net/live/{stream_id}{src_suffix}"
                    
                    if screen_type != "SINGLE":
                        new_entry["poolId"] = f"{stream_id}{bowl_suffix}"
                    
                    pool_entry["gamelist"].append(new_entry)
                
                json_data["pool"].append(pool_entry)
        
        return {
            "status": "success",
            "json_content": json.dumps(json_data, indent=4),
            "filename": "list-new.json"
        }
    
    def read_image_recon_json(self) -> Dict:
        """Read image-recon.json file"""
        json_file_path = '/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json'
        
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            return {"status": "success", "data": data}
        except FileNotFoundError:
            return {"status": "error", "message": "File not found"}
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON format: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Error reading file: {str(e)}"}
    
    def get_image_recon_servers(self) -> List[Dict]:
        """Get list of server IPs from image-recon.json (same as Image Recon Service)"""
        # Try multiple possible paths for the image-recon.json file
        json_file_paths = [
            '/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json',
            '/opt/compose-conf/prometheus/image-recon.json',
            '/opt/compose-conf/image-recon.json',
            os.path.join(settings.TYPE_DIR, 'ir.json')  # Fallback for local dev
        ]
        
        for json_file_path in json_file_paths:
            if not os.path.exists(json_file_path):
                logger.info(f"⏭️  Skipping (not found): {json_file_path}")
                continue
        
            try:
                with open(json_file_path, 'r') as f:
                    data = json.load(f)
            
                servers = []
                if isinstance(data, list):
                    for item in data:
                        targets = item.get('targets', [])
                        for target in targets:
                            ip = target.split(':')[0]
                            hostname = item.get('labels', {}).get('hostname', 'Unknown Host')
                            label = hostname.split('-')[0]
                        
                            # Filter out SRS servers
                            if label.upper() != 'SRS':
                                servers.append({
                                    "ip": ip,
                                    "hostname": hostname,
                                    "label": label
                                })
            
                logger.info(f"✅ Loaded {len(servers)} servers from: {json_file_path}")
                return servers
            except Exception as e:
                logger.error(f"❌ Error reading {json_file_path}: {e}")
                continue
        
        # If no config files found, use mock data for local development
        logger.warning("⚠️ No config files found in any location - using mock data for development")
        return self._get_mock_servers()
    
    def _get_mock_servers(self) -> List[Dict]:
        """Return mock server data for development/testing"""
        return [
            {"ip": "10.100.1.10", "hostname": "NP-1", "label": "NP"},
            {"ip": "10.100.1.11", "hostname": "NP-2", "label": "NP"},
            {"ip": "10.100.2.10", "hostname": "TW-1", "label": "TW"},
            {"ip": "10.100.2.11", "hostname": "TW-2", "label": "TW"},
        ]
    
    def fetch_file_from_server(self, server_ip: str, remote_file_path: str) -> str:
        """Fetch file content from server via SSH"""
        if not SSH_AVAILABLE:
            raise Exception("SSH functionality not available. Install paramiko and scp packages.")
        
        # Use Image Recon credentials (root + image-recon-prod.pem)
        ssh_key_path = 'static/keys/image-recon-prod.pem'
        ssh_username = 'root'
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if not os.path.exists(ssh_key_path):
                raise ValueError(f"Private key file does not exist at path: {ssh_key_path}")
            
            private_key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
            ssh.connect(server_ip, username=ssh_username, pkey=private_key, timeout=30)
            
            # Execute cat command to read file
            stdin, stdout, stderr = ssh.exec_command(f'cat {remote_file_path}')
            content = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            ssh.close()
            
            if error and 'No such file or directory' in error:
                raise Exception(f"File not found: {remote_file_path}")
            elif error:
                raise Exception(f"Error reading file: {error}")
            
            return content
        except Exception as e:
            raise Exception(f"Failed to fetch file from {server_ip}: {str(e)}")
    
    def send_file_to_server(self, server_ip: str, local_file_path: str, remote_file_path: str) -> Tuple[bool, str]:
        """Send file to server using SCP"""
        if not SSH_AVAILABLE:
            return False, "SSH functionality not available. Install paramiko and scp packages."
        
        # Use Image Recon credentials (root + image-recon-prod.pem)
        ssh_key_path = 'static/keys/image-recon-prod.pem'
        ssh_username = 'root'
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if not os.path.exists(ssh_key_path):
                raise ValueError(f"Private key file does not exist at path: {ssh_key_path}")
            
            private_key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
            ssh.connect(server_ip, username=ssh_username, pkey=private_key, timeout=30)
            
            scp = SCPClient(ssh.get_transport())
            scp.put(local_file_path, remote_file_path)
            
            scp.close()
            ssh.close()
            
            return True, "File sent successfully"
        except Exception as e:
            return False, str(e)
    
    def send_json_to_servers(self, json_content: str, servers: List[Dict], remote_path: str) -> Dict:
        """Send JSON file to selected servers"""
        try:
            # Validate JSON format
            json.loads(json_content)
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON format: {str(e)}"}
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write(json_content)
            temp_file_path = temp_file.name
        
        results = []
        
        try:
            for server in servers:
                server_ip = server.get('ip')
                server_hostname = server.get('hostname', 'Unknown')
                
                if not server_ip:
                    results.append({
                        "server": server_hostname,
                        "ip": server_ip,
                        "status": "error",
                        "message": "No IP address provided"
                    })
                    continue
                
                success, message = self.send_file_to_server(server_ip, temp_file_path, remote_path)
                
                results.append({
                    "server": server_hostname,
                    "ip": server_ip,
                    "status": "success" if success else "error",
                    "message": message
                })
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
