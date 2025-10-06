import json
import os
import tempfile
import time
import re
import logging
import smtplib
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings
from .logger import logger

try:
    import paramiko
    SSH_AVAILABLE = True
except ImportError:
    SSH_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

def send_lark_notification(server_ip: str, hostname: str, status: str, message: str, error: str = None):
    """Send restart notification to Lark webhook - matches Flask version exactly"""
    if not REQUESTS_AVAILABLE:
        return
    
    try:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Determine status emoji and text
        if status == "success":
            status_emoji = "✅"
            status_text = "SUCCESS"
        elif status == "warning":
            status_emoji = "⚠️"
            status_text = "WARNING"
        else:
            status_emoji = "❌"
            status_text = "FAILED"
        
        # Create message (matches Flask format exactly)
        message_lines = [
            f"🔄 **OSM Service Restart Notification**",
            f"📅 **Time:** {timestamp}",
            f"🖥️ **Server:** {hostname} ({server_ip})",
            f"{status_emoji} **Status:** {status_text}",
            f"📝 **Message:** {message}"
        ]
        
        if error:
            message_lines.append(f"❌ **Error:** {error}")
        
        message_text = "\n".join(message_lines)
        
        # Prepare webhook body
        body = {
            "msg_type": "text",
            "content": {
                "text": message_text
            }
        }
        
        # Send to Lark webhook
        logger.info(f"📤 Sending restart notification to Lark webhook...")
        response = requests.post(settings.LARK_WEBHOOK_URL, headers=headers, json=body, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Restart notification sent successfully to Lark")
        else:
            logger.error(f"❌ Failed to send restart notification to Lark webhook: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error sending restart notification to Lark: {str(e)}")

class ImageReconServiceManager:
    def __init__(self):
        # Use root user and production key for Image Recon servers
        self.ssh_username = "root"
        self.ssh_key_filename = "image-recon-prod.pem"
        self.ssh_key_path = os.path.join('static', 'keys', self.ssh_key_filename)
        
        # Version cache: {server_ip: {'version': str, 'timestamp': datetime}}
        self._version_cache = {}
        self._version_cache_duration = 600  # 10 minutes in seconds
        self.email_config_path = os.path.join(settings.TYPE_DIR, 'email.json')
        self.server_cache = {}
        self.last_cache_update = 0
        self.cache_ttl = 300  # 5 minutes cache
        
        # Ensure email config exists
        self._ensure_email_config()
    
    def get_image_recon_servers(self) -> List[Dict]:
        """Get list of server IPs from image-recon.json"""
        # Try multiple possible paths for the image-recon.json file
        json_file_paths = [
            '/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json',
            '/opt/compose-conf/prometheus/image-recon.json',
            '/opt/compose-conf/image-recon.json',
            os.path.join(settings.TYPE_DIR, 'ir.json')  # Fallback for local dev
        ]
        
        for json_file_path in json_file_paths:
            if not os.path.exists(json_file_path):
                print(f"⏭️  Skipping (not found): {json_file_path}")
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
                            
                            # Filter out SRS servers for restart operations
                            if label.upper() != 'SRS':
                                servers.append({
                                    "ip": ip,
                                    "hostname": hostname,
                                    "label": label,
                                    "status": "unknown"
                                })
                
                print(f"✅ Loaded {len(servers)} servers from: {json_file_path}")
                return servers
            except Exception as e:
                print(f"❌ Error reading {json_file_path}: {e}")
                continue
        
        # If no config files found, use mock data
        print("⚠️ No config files found in any location - using mock data for development")
        return self._get_mock_servers()
    
    def _get_mock_servers(self) -> List[Dict]:
        """Return mock server data for development/testing"""
        return [
            {
                "ip": "10.100.4.100",
                "hostname": "image-recon-server-01",
                "label": "IR-01",
                "status": "development"
            },
            {
                "ip": "10.100.4.101", 
                "hostname": "image-recon-server-02",
                "label": "IR-02",
                "status": "development"
            },
            {
                "ip": "10.100.4.102",
                "hostname": "image-recon-server-03", 
                "label": "IR-03",
                "status": "development"
            }
        ]
    
    def _ensure_email_config(self):
        """Ensure email configuration file exists with default settings"""
        if not os.path.exists(self.email_config_path):
            default_config = {
                "recipients": ["admin@example.com"],
                "schedule": {
                    "enabled": False,
                    "day": "monday",
                    "time": "09:30",
                    "timezone": "Asia/Kuala_Lumpur"
                },
                "smtp": {
                    "server": "smtp.gmail.com",
                    "port": 587,
                    "username": "",
                    "password": "",
                    "use_tls": True
                }
            }
            
            os.makedirs(os.path.dirname(self.email_config_path), exist_ok=True)
            with open(self.email_config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
    
    def load_email_config(self) -> Dict:
        """Load email configuration from JSON file"""
        try:
            with open(self.email_config_path, 'r') as f:
                return json.load(f)
        except Exception:
            self._ensure_email_config()
            with open(self.email_config_path, 'r') as f:
                return json.load(f)
    
    def save_email_config(self, config: Dict) -> bool:
        """Save email configuration to JSON file"""
        try:
            with open(self.email_config_path, 'w') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving email config: {e}")
            return False
    
    def search_machines(self, query: str) -> List[Dict]:
        """Search for machines in ir.json by machine ID - matches Flask version"""
        if not query or len(query.strip()) < 2:
            return []
        
        # Read server data from ir.json with caching
        server_groups = self._get_cached_server_data_from_ir_json()
        
        if not server_groups:
            logger.warning("No server data available in ir.json for search")
            return []
        
        matching_servers = []
        query_lower = query.lower().strip()
        max_results = 5  # Limit results for faster response (matches Flask)
        
        # Search for the query in machine IDs
        for label, servers in server_groups.items():
            if len(matching_servers) >= max_results:
                break
            
            for server in servers:
                if len(matching_servers) >= max_results:
                    break
                
                hostname = server.get('hostname', 'Unknown Host')
                ids = server.get('ids', [])
                
                # Search for the query in the ids list (case-insensitive)
                matching_ids = [id_obj['id'] for id_obj in ids if query_lower in id_obj['id'].lower()]
                
                if matching_ids:
                    matching_servers.append({
                        "hostname": hostname,
                        "matching_ids": matching_ids,
                        "label": label
                    })
        
        logger.info(f"🔍 Search for '{query}': Found {len(matching_servers)} matching servers")
        return matching_servers
    
    def _get_cached_server_data_from_ir_json(self) -> Dict:
        """Get server data from ir.json with caching"""
        current_time = time.time()
        
        # Check if cache is still valid
        if self.server_cache and (current_time - self.last_cache_update < self.cache_ttl):
            return self.server_cache
        
        # Cache miss or expired - read from file
        json_file_path = os.path.join(settings.TYPE_DIR, 'ir.json')
        
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Ensure data is a dictionary with labels as keys
            if isinstance(data, dict):
                self.server_cache = data
                self.last_cache_update = current_time
                return data
            else:
                logger.error("ir.json structure is not a dictionary")
                return {}
                
        except FileNotFoundError:
            logger.warning(f"ir.json not found at {json_file_path}. Run refresh to create it.")
            return {}
        except Exception as e:
            logger.error(f"📄 Error reading ir.json: {str(e)}")
            return {}
    
    def get_server_logs(self, server_ip: str, lines: int = 50) -> Tuple[bool, str]:
        """Get logs from a specific server"""
        if not SSH_AVAILABLE:
            return False, "SSH functionality not available"
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if not os.path.exists(self.ssh_key_path):
                return False, f"SSH key not found: {self.ssh_key_path}"
            
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=10)
            
            # Get logs from common locations
            log_commands = [
                f"tail -{lines} /usr/bin/OSMWatcher/logs/image_identifier.log 2>/dev/null",
                f"tail -{lines} /var/log/image_recon.log 2>/dev/null",
                f"tail -{lines} /opt/logs/service.log 2>/dev/null"
            ]
            
            for cmd in log_commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                logs = stdout.read().decode('utf-8').strip()
                
                if logs:
                    ssh.close()
                    return True, logs
            
            ssh.close()
            return False, "No logs found in common locations"
            
        except Exception as e:
            return False, f"Error getting logs: {str(e)}"
    
    def check_server_status(self, server_ip: str) -> Dict:
        """Check the status and version of a server"""
        if not SSH_AVAILABLE:
            return {"status": "error", "message": "SSH not available"}
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if not os.path.exists(self.ssh_key_path):
                return {"status": "error", "message": f"SSH key not found: {self.ssh_key_path}"}
            
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=10)
            
            # Check service status
            stdin, stdout, stderr = ssh.exec_command("systemctl is-active image-recon || service image-recon status")
            service_status = stdout.read().decode('utf-8').strip()
            
            # Check version
            stdin, stdout, stderr = ssh.exec_command("cat /usr/bin/OSMWatcher/version.txt 2>/dev/null || echo 'unknown'")
            version = stdout.read().decode('utf-8').strip()
            
            # Check uptime
            stdin, stdout, stderr = ssh.exec_command("uptime")
            uptime = stdout.read().decode('utf-8').strip()
            
            ssh.close()
            
            return {
                "status": "success",
                "service_status": service_status,
                "version": version,
                "uptime": uptime,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Error checking status: {str(e)}"}
    
    def batch_update_servers(self, servers: List[Dict], update_file: str = None) -> Dict:
        """Perform batch update on multiple servers"""
        if not SSH_AVAILABLE:
            return {"status": "error", "message": "SSH functionality not available"}
        
        results = []
        total_servers = len(servers)
        
        for i, server in enumerate(servers):
            server_ip = server.get('ip')
            hostname = server.get('hostname', server_ip)
            
            try:
                # Simulate update process (replace with actual update logic)
                result = self._update_single_server(server_ip, update_file)
                result['hostname'] = hostname
                result['progress'] = f"{i+1}/{total_servers}"
                results.append(result)
                
            except Exception as e:
                results.append({
                    "hostname": hostname,
                    "ip": server_ip,
                    "status": "error",
                    "message": str(e),
                    "progress": f"{i+1}/{total_servers}"
                })
        
        return {
            "status": "success",
            "results": results,
            "total": total_servers,
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_single_server(self, server_ip: str, update_file: str = None) -> Dict:
        """Update a single server"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if not os.path.exists(self.ssh_key_path):
                return {"status": "error", "message": f"SSH key not found: {self.ssh_key_path}"}
            
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=30)
            
            # Stop service
            stdin, stdout, stderr = ssh.exec_command("sudo systemctl stop image-recon")
            stdout.read()
            
            # Update files (if update_file provided)
            if update_file:
                # Upload and extract update file
                stdin, stdout, stderr = ssh.exec_command(f"cd /usr/bin/OSMWatcher && sudo tar -xzf {update_file}")
                stdout.read()
            
            # Start service
            stdin, stdout, stderr = ssh.exec_command("sudo systemctl start image-recon")
            stdout.read()
            
            # Verify service is running
            time.sleep(2)
            stdin, stdout, stderr = ssh.exec_command("systemctl is-active image-recon")
            status = stdout.read().decode('utf-8').strip()
            
            ssh.close()
            
            return {
                "status": "success" if status == "active" else "warning",
                "message": f"Update completed, service is {status}",
                "service_status": status
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Update failed: {str(e)}"}
    
    def send_batch_email(self, recipients: List[str], subject: str, message: str, results: List[Dict] = None) -> Dict:
        """Send batch email notifications"""
        try:
            config = self.load_email_config()
            smtp_config = config.get('smtp', {})
            
            if not smtp_config.get('username') or not smtp_config.get('password'):
                return {"status": "error", "message": "SMTP configuration incomplete"}
            
            # Create email content
            msg = MIMEMultipart()
            msg['From'] = smtp_config['username']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Build email body
            body = f"{message}\n\n"
            
            if results:
                body += "Operation Results:\n"
                body += "=" * 50 + "\n"
                
                for result in results:
                    hostname = result.get('hostname', 'Unknown')
                    status = result.get('status', 'Unknown')
                    message = result.get('message', '')
                    body += f"• {hostname}: {status.upper()}"
                    if message:
                        body += f" - {message}"
                    body += "\n"
                
                body += "\n" + "=" * 50 + "\n"
                body += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
            if smtp_config.get('use_tls', True):
                server.starttls()
            
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
            server.quit()
            
            return {
                "status": "success",
                "message": f"Email sent to {len(recipients)} recipients",
                "recipients": recipients
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}
    
    def execute_ssh_command(self, server_ip: str, command: str) -> Tuple[bool, str]:
        """Execute SSH command on remote server"""
        if not SSH_AVAILABLE:
            return False, "SSH functionality not available. Install paramiko package."
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if not os.path.exists(self.ssh_key_path):
                raise ValueError(f"Private key file does not exist at path: {self.ssh_key_path}")
            
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=30)
            
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # Wait for command to complete
            exit_status = stdout.channel.recv_exit_status()
            
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            ssh.close()
            
            if exit_status == 0:
                return True, output.strip()
            else:
                return False, error.strip() or f"Command failed with exit status {exit_status}"
                
        except Exception as e:
            return False, str(e)
    
    def restart_service(self, servers: List[Dict], service_name: str = "image-recognition") -> Dict:
        """Restart service on selected servers"""
        results = []
        
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
            
            # Command to restart the service (adjust based on your actual service management)
            restart_command = f"sudo systemctl restart {service_name}"
            
            success, message = self.execute_ssh_command(server_ip, restart_command)
            
            results.append({
                "server": server_hostname,
                "ip": server_ip,
                "status": "success" if success else "error",
                "message": message or "Service restarted successfully"
            })
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def clear_version_cache(self, server_ip: str = None):
        """Clear version cache for a specific server or all servers"""
        if server_ip:
            if server_ip in self._version_cache:
                del self._version_cache[server_ip]
                logger.info(f"🗑️ Cleared version cache for {server_ip}")
        else:
            self._version_cache.clear()
            logger.info("🗑️ Cleared all version cache")
    
    def get_server_ids(self, server_ip: str) -> List[Dict]:
        """Get server IDs from list.json on remote server - matches Flask version"""
        if not SSH_AVAILABLE:
            logger.error(f"[{server_ip}] SSH not available")
            return []
        
        try:
            # Check if SSH key exists
            if not os.path.exists(self.ssh_key_path):
                logger.error(f"Private key not found at: {self.ssh_key_path}")
                return []
            
            logger.info(f"🔌 Attempting to SSH into server {server_ip}")
            
            # Create an SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load private key
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            
            # Connect to the server
            ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=30)
            
            logger.info(f"✅ Successfully connected to {server_ip}")
            
            # Run the command to fetch the ids from list.json
            command = "cat /usr/bin/OSMWatcher/list.json | grep -oP '\"id\": \"[^\"]+'"
            logger.info(f"🔍 Running command: {command}")
            
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # Capture the results from stdout
            ids = stdout.read().decode()
            
            ssh.close()
            
            # Check if there were any results
            if not ids:
                logger.warning(f"⚠️ No IDs found for server {server_ip}")
                return []
            
            # Clean the results by removing extra characters and extracting the IDs
            cleaned_ids = [line.split(":")[1].strip().replace('"', '') for line in ids.splitlines()]
            
            # Prepare the cleaned IDs in the desired format
            id_objects = [{"id": id.strip()} for id in cleaned_ids]
            
            logger.info(f"📋 Fetched {len(id_objects)} IDs for {server_ip}")
            
            return id_objects
            
        except Exception as e:
            logger.error(f"📄 Error reading list.json from {server_ip}: {str(e)}")
            return []
    
    def refresh_servers(self) -> Dict:
        """Refresh server list by fetching IDs from each server and updating ir.json - matches Flask version"""
        try:
            logger.info("=" * 80)
            logger.info("🔄 SERVER REFRESH INITIATED")
            logger.info("=" * 80)
            
            # Read server groups from image-recon.json
            server_groups = self.get_image_recon_servers()
            
            if not server_groups:
                return {"status": "error", "message": "No servers found in image-recon.json"}
            
            # Initialize the result data structure
            refreshed_data = {}
            total_servers = 0
            successful_fetches = 0
            
            # Loop through the servers and fetch the IDs for each server
            for label, servers in server_groups.items():
                refreshed_data[label] = []
                
                for server in servers:
                    server_ip = server['ip']
                    hostname = server['hostname']
                    total_servers += 1
                    
                    # Fetch the server IDs by SSH'ing into the server
                    ids = self.get_server_ids(server_ip)
                    
                    if ids:
                        successful_fetches += 1
                        refreshed_data[label].append({
                            "hostname": hostname,
                            "ids": ids
                        })
                    else:
                        refreshed_data[label].append({
                            "hostname": hostname,
                            "ids": []  # If no IDs were fetched, set an empty list
                        })
            
            # Define the path to store the JSON file (ir.json)
            json_file_path = os.path.join(settings.TYPE_DIR, 'ir.json')
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
            
            # Write the refreshed server list to the JSON file
            with open(json_file_path, 'w') as f:
                json.dump(refreshed_data, f, indent=4)
            
            logger.info(f"🔄 Server list has been refreshed and written to {json_file_path}")
            
            # Invalidate cache after refresh
            self.server_cache = {}
            self.last_cache_update = 0
            logger.info("🗑️ Cache invalidated after server refresh")
            
            logger.info("=" * 80)
            logger.info(f"📊 REFRESH COMPLETED: {successful_fetches}/{total_servers} servers successful")
            logger.info("=" * 80)
            
            return {
                "status": "success",
                "message": "Server list refreshed successfully!",
                "total_servers": total_servers,
                "successful_fetches": successful_fetches
            }
            
        except Exception as e:
            logger.error(f"🔄 Error refreshing server list: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _get_server_version(self, server_ip: str) -> str:
        """Get version from server using journalctl with 10-minute cache"""
        if not SSH_AVAILABLE:
            logger.warning(f"[{server_ip}] SSH not available")
            return "Unknown"
        
        # Check cache first (10-minute cache to reduce SSH connections)
        current_time = time.time()
        if server_ip in self._version_cache:
            cache_entry = self._version_cache[server_ip]
            cache_age = current_time - cache_entry['timestamp']
            
            # If cache is still valid (less than 10 minutes old), return cached version
            if cache_age < self._version_cache_duration:
                return cache_entry['version']
        
        # Cache miss or expired - fetch from server via SSH
        try:
            # Confirm that the private key exists
            if not os.path.exists(self.ssh_key_path):
                logger.error(f"[{server_ip}] Key not found: {self.ssh_key_path}")
                return "Unknown"
            
            # Create an SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load the private key for authentication
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            
            # Attempt SSH connection with a timeout
            ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=10)
            
            # Run journalctl command to get version (exactly like Flask)
            version_cmd = 'journalctl --since "10 minutes ago" | grep -o "version\\[[0-9]\\+\\.[0-9]\\+\\.[0-9]\\+-[0-9]\\+]" | tail -1'
            
            stdin, stdout, stderr = ssh.exec_command(version_cmd, timeout=10)
            version_output = stdout.read().decode().strip()
            
            ssh.close()
            
            # Extract version from format: version[3.1.2335-1]
            version = "Unknown"
            if version_output and version_output.startswith('version['):
                import re
                version_match = re.search(r'version\[([0-9]+\.[0-9]+\.[0-9]+-[0-9]+)\]', version_output)
                if version_match:
                    version = version_match.group(1)
            else:
                # Only log if version not found (warning)
                logger.warning(f"[{server_ip}] ⚠️ No version found in journalctl output")
            
            # Update cache with new version and timestamp
            self._version_cache[server_ip] = {
                'version': version,
                'timestamp': current_time
            }
            
            return version
            
        except Exception as e:
            logger.error(f"[{server_ip}] ❌ Error getting version: {e}")
            return "Unknown"
    
    def _get_logs_from_server(self, server_ip: str, lines: int = 100) -> str:
        """Get logs from server using journalctl - matches Flask version exactly"""
        if not SSH_AVAILABLE:
            return "Error: SSH not available"
        
        try:
            # Confirm that the private key exists
            if not os.path.exists(self.ssh_key_path):
                return f"Error: Private key file does not exist at path: {self.ssh_key_path}"
            
            # Create an SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load the private key for authentication
            private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
            
            # Attempt SSH connection with a timeout
            ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=60)
            
            # Run journalctl to fetch logs (exactly like Flask version)
            command = f"journalctl -u osm -n {lines}"
            
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # Read the logs
            logs = stdout.read().decode()
            
            # If there's an error from stderr, raise an exception
            error_message = stderr.read().decode()
            if error_message:
                raise Exception(f"Error fetching logs: {error_message}")
            
            ssh.close()
            
            # If no logs are returned, handle it gracefully
            if not logs:
                logs = "No logs available."
            
            return logs
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def check_service_status(self, servers: List[Dict], service_name: str = "osm") -> Dict:
        """Check service status and version on selected servers - matches Flask version"""
        results = []
        
        for server in servers:
            server_ip = server.get('ip')
            server_hostname = server.get('hostname', 'Unknown')
            
            if not server_ip:
                results.append({
                    "server": server_hostname,
                    "ip": server_ip,
                    "status": "error",
                    "version": "Unknown",
                    "message": "No IP address provided"
                })
                continue
            
            try:
                # Get version using SSH command (exactly like Flask version)
                version = self._get_server_version(server_ip)
                
                # Get logs to check status
                logs = self._get_logs_from_server(server_ip, lines=100)
                
                # Check if we got logs successfully
                if "Error:" in logs:
                    results.append({
                        "server": server_hostname,
                        "ip": server_ip,
                        "status": "offline",
                        "version": version,
                        "message": logs
                    })
                    continue
                
                # Check for offline indicators
                offline_indicators = ["stopped osm service"]
                is_offline = any(indicator in logs.lower() for indicator in offline_indicators)
                
                # Check for error indicators
                error_indicators = [
                    "exception caught: stoi",
                    "system error",
                    "segmentation fault",
                    "cannot open connection",
                    "core dumped"
                ]
                has_errors = any(indicator in logs.lower() for indicator in error_indicators)
                
                status = "offline" if is_offline else ("error" if has_errors else "online")
                
                results.append({
                    "server": server_hostname,
                    "ip": server_ip,
                    "status": status,
                    "version": version,
                    "message": "Service is running" if status == "online" else f"Service has issues: {status}"
                })
                
            except Exception as e:
                results.append({
                    "server": server_hostname,
                    "ip": server_ip,
                    "status": "error",
                    "version": "Unknown",
                    "message": f"Error checking status: {str(e)}"
                })
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def restart_machine(self, servers: List[Dict]) -> Dict:
        """Restart entire machine on selected servers"""
        results = []
        
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
            
            # Command to restart the machine
            restart_command = "sudo reboot"
            
            success, message = self.execute_ssh_command(server_ip, restart_command)
            
            results.append({
                "server": server_hostname,
                "ip": server_ip,
                "status": "success" if success else "error",
                "message": message or "Machine restart initiated"
            })
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def restart_service(self, servers: List[Dict], service_name: str = "osm", initiated_by: str = "Unknown") -> Dict:
        """Restart service on multiple servers - matches Flask version"""
        if not SSH_AVAILABLE:
            return {"status": "error", "message": "SSH functionality not available"}
        
        # Log who initiated the restart
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 80)
        logger.info(f"🔄 SERVICE RESTART INITIATED")
        logger.info(f"📅 Time: {timestamp}")
        logger.info(f"👤 Initiated by: {initiated_by}")
        logger.info(f"🎯 Target servers: {len(servers)}")
        logger.info(f"🔧 Service: {service_name}")
        logger.info("=" * 80)
        
        results = []
        
        for server in servers:
            server_ip = server.get('ip')
            hostname = server.get('hostname', server_ip)
            
            try:
                logger.info(f"🔄 Attempting to restart service on {server_ip} ({hostname})")
                
                # Connect via SSH
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                private_key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
                ssh.connect(server_ip, username=self.ssh_username, pkey=private_key, timeout=30)
                
                logger.info(f"✅ Connected to {server_ip}. Restarting service...")
                
                # Restart command: restart service, wait 10 seconds, check if active
                # Since we're root, no sudo password needed
                restart_command = f"systemctl restart {service_name} && sleep 10 && systemctl is-active {service_name}"
                
                stdin, stdout, stderr = ssh.exec_command(restart_command, timeout=180)
                
                # Wait for completion (up to 3 minutes)
                start_time = time.time()
                timeout = 180
                
                logger.info(f"⏳ Waiting for restart command to complete...")
                while not stdout.channel.exit_status_ready():
                    if time.time() - start_time > timeout:
                        ssh.close()
                        logger.error(f"⏰ Restart timeout after {timeout} seconds on {server_ip}")
                        msg = f"Restart timeout after {timeout} seconds. Service may still be restarting."
                        results.append({
                            "hostname": hostname,
                            "ip": server_ip,
                            "status": "error",
                            "message": msg
                        })
                        # Send timeout notification to Lark (matches Flask exactly - with "Timeout" error)
                        send_lark_notification(server_ip, hostname, "error", msg, "Timeout")
                        continue
                    time.sleep(1)
                
                # Check exit status
                exit_status = stdout.channel.recv_exit_status()
                service_status = stdout.read().decode().strip()
                
                ssh.close()
                
                logger.info(f"📊 Service status after restart: {service_status}")
                
                if exit_status == 0 and service_status == "active":
                    logger.info(f"🎉 Service restarted successfully and is ACTIVE on {server_ip}")
                    msg = "Service restarted successfully and is now active."
                    results.append({
                        "hostname": hostname,
                        "ip": server_ip,
                        "status": "success",
                        "message": msg
                    })
                    # Send success notification to Lark (matches Flask exactly)
                    send_lark_notification(server_ip, hostname, "success", msg)
                elif exit_status == 0:
                    logger.warning(f"⚠️ Service restarted but status is '{service_status}' on {server_ip}")
                    msg = f"Service restarted but current status is: {service_status}. Please check manually."
                    results.append({
                        "hostname": hostname,
                        "ip": server_ip,
                        "status": "warning",
                        "message": msg
                    })
                    # Send warning notification to Lark (matches Flask exactly)
                    send_lark_notification(server_ip, hostname, "warning", msg)
                else:
                    error_msg = stderr.read().decode().strip()
                    msg = f"Failed to restart the service. {error_msg}" if error_msg else "Failed to restart the service."
                    logger.error(f"💥 Error restarting service on {server_ip}: {error_msg}")
                    results.append({
                        "hostname": hostname,
                        "ip": server_ip,
                        "status": "error",
                        "message": msg
                    })
                    # Send error notification to Lark (matches Flask exactly - with error detail)
                    send_lark_notification(server_ip, hostname, "error", msg, error_msg if error_msg else None)
            
            except Exception as e:
                error_str = str(e)
                msg = f"Unexpected error during restart: {error_str}"
                logger.error(f"Error: {error_str}")  # Match Flask log format
                results.append({
                    "hostname": hostname,
                    "ip": server_ip,
                    "status": "error",
                    "message": error_str
                })
                # Send error notification to Lark (matches Flask exactly)
                send_lark_notification(server_ip, hostname, "error", msg, error_str)
        
        # Log restart summary
        success_count = sum(1 for r in results if r.get('status') == 'success')
        warning_count = sum(1 for r in results if r.get('status') == 'warning')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        
        logger.info("=" * 80)
        logger.info(f"📊 RESTART OPERATION COMPLETED")
        logger.info(f"✅ Success: {success_count} | ⚠️ Warning: {warning_count} | ❌ Error: {error_count}")
        logger.info(f"👤 Initiated by: {initiated_by}")
        logger.info("=" * 80)
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def check_service_status(self, servers: List[Dict], service_name: str = "image-recon") -> Dict:
        """Check service status on multiple servers"""
        results = []
        
        for server in servers:
            server_ip = server.get('ip')
            hostname = server.get('hostname', server_ip)
            
            try:
                status_result = self.check_server_status(server_ip)
                results.append({
                    "hostname": hostname,
                    "ip": server_ip,
                    "status": status_result.get("status", "error"),
                    "service_status": status_result.get("service_status", "unknown"),
                    "version": status_result.get("version", "unknown"),
                    "uptime": status_result.get("uptime", "unknown")
                })
            
            except Exception as e:
                logger.error(f"❌ Error checking status on {server_ip}: {str(e)}")
                results.append({
                    "hostname": hostname,
                    "ip": server_ip,
                    "status": "error",
                    "message": str(e)
                })
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
