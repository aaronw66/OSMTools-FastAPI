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

class ImageReconServiceManager:
    def __init__(self):
        # Use root user and production key for Image Recon servers
        self.ssh_username = "root"
        self.ssh_key_filename = "image-recon-prod.pem"
        self.ssh_key_path = os.path.join(settings.STATIC_DIR, 'keys', self.ssh_key_filename)
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
        """Search for machines by hostname or ID"""
        if not query or len(query.strip()) < 2:
            return []
        
        servers = self.get_image_recon_servers()
        matching_servers = []
        query_lower = query.lower().strip()
        
        for server in servers:
            hostname = server.get('hostname', '').lower()
            ip = server.get('ip', '').lower()
            label = server.get('label', '').lower()
            
            # Search in hostname, IP, or label
            if (query_lower in hostname or 
                query_lower in ip or 
                query_lower in label):
                matching_servers.append(server)
                
                # Limit results for performance
                if len(matching_servers) >= 10:
                    break
        
        return matching_servers
    
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
                # Get logs to check version and status (like Flask version)
                logs = self._get_logs_from_server(server_ip, lines=100)
                
                # Check if we got logs successfully
                if "Error:" in logs:
                    results.append({
                        "server": server_hostname,
                        "ip": server_ip,
                        "status": "offline",
                        "version": "Unknown",
                        "message": logs
                    })
                    continue
                
                # Extract version from logs (look for version pattern like "3.1.2306-1")
                version = "Unknown"
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+-\d+)', logs)
                if version_match:
                    version = version_match.group(1)
                
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
    
    def restart_service(self, servers: List[Dict], service_name: str = "image-recon") -> Dict:
        """Restart service on multiple servers"""
        if not SSH_AVAILABLE:
            return {"status": "error", "message": "SSH functionality not available"}
        
        results = []
        
        for server in servers:
            server_ip = server.get('ip')
            hostname = server.get('hostname', server_ip)
            
            try:
                # Execute restart command
                success, output = self.execute_ssh_command(
                    server_ip, 
                    f"sudo systemctl restart {service_name}"
                )
                
                if success:
                    # Verify service is running
                    time.sleep(2)
                    success, status_output = self.execute_ssh_command(
                        server_ip,
                        f"systemctl is-active {service_name}"
                    )
                    
                    results.append({
                        "hostname": hostname,
                        "ip": server_ip,
                        "status": "success" if success and "active" in status_output else "warning",
                        "message": f"Service restarted, status: {status_output}" if success else "Service restarted but status unknown"
                    })
                else:
                    results.append({
                        "hostname": hostname,
                        "ip": server_ip,
                        "status": "error",
                        "message": f"Failed to restart service: {output}"
                    })
            
            except Exception as e:
                results.append({
                    "hostname": hostname,
                    "ip": server_ip,
                    "status": "error",
                    "message": f"Error: {str(e)}"
                })
        
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
