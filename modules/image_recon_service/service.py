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
    
    def add_email_recipient(self, email: str) -> tuple:
        """Add new recipient to the email list - matches Flask version"""
        try:
            config = self.load_email_config()
            
            # Check if email already exists (case-insensitive)
            if email.lower() in [r.lower() for r in config["recipients"]]:
                return False, "Email already exists in the recipient list"
            
            # Add the email
            config["recipients"].append(email)
            
            # Save configuration
            if self.save_email_config(config):
                logger.info(f"📧 Added email recipient: {email}")
                return True, f"Recipient {email} added successfully"
            else:
                return False, "Failed to save configuration"
                
        except Exception as e:
            logger.error(f"❌ Error adding email recipient: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def remove_email_recipient(self, email: str) -> tuple:
        """Remove recipient from the email list - matches Flask version"""
        try:
            config = self.load_email_config()
            original_count = len(config["recipients"])
            
            # Remove the email (case-insensitive)
            config["recipients"] = [r for r in config["recipients"] if r.lower() != email.lower()]
            
            # Check if we're trying to remove the last recipient
            if len(config["recipients"]) == 0:
                return False, "Cannot remove all recipients. At least one recipient is required."
            
            # Check if email was found
            if len(config["recipients"]) == original_count:
                return False, "Email address not found in recipient list"
            
            # Save configuration
            if self.save_email_config(config):
                logger.info(f"📧 Removed email recipient: {email}")
                return True, f"Recipient {email} removed successfully"
            else:
                return False, "Failed to save configuration"
                
        except Exception as e:
            logger.error(f"❌ Error removing email recipient: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def toggle_schedule(self, enabled: bool) -> tuple:
        """Enable or disable scheduled version check - matches Flask version"""
        try:
            config = self.load_email_config()
            config["schedule"]["enabled"] = enabled
            
            # Update last_run timestamp when enabling
            if enabled:
                config["schedule"]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if self.save_email_config(config):
                status = "enabled" if enabled else "disabled"
                logger.info(f"⏰ Scheduled version check {status}")
                return True, f"Scheduled version check {status}"
            else:
                return False, "Failed to save schedule settings"
                
        except Exception as e:
            logger.error(f"❌ Error toggling schedule: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def test_scheduled_version_check(self) -> Dict:
        """Test the scheduled version check by running it immediately - matches Flask version"""
        try:
            logger.info("🕘 Running test version check...")
            
            # Get current recipients
            config = self.load_email_config()
            recipients = config.get("recipients", [])
            
            if not recipients:
                return {
                    "status": "error",
                    "message": "No recipients configured for version check"
                }
            
            logger.info(f"📧 Test version check will send to: {', '.join(recipients)}")
            
            # Get all servers
            servers = self.get_image_recon_servers()
            if not servers:
                return {
                    "status": "error",
                    "message": "No servers found"
                }
            
            # Check versions on all servers
            version_results = []
            successful_checks = 0
            failed_checks = 0
            
            logger.info(f"🔍 Checking versions on {len(servers)} servers")
            
            # First pass: collect all versions to find the most common one (target version)
            all_versions = []
            for server in servers:
                try:
                    version = self._get_server_version(server.get('ip'))
                    if version and version != 'N/A' and version != 'Error' and version != 'Offline' and version != 'Unknown':
                        all_versions.append(version)
                except Exception:
                    pass
            
            # Determine target version (most common version)
            from collections import Counter
            if all_versions:
                version_counts = Counter(all_versions)
                target_version = version_counts.most_common(1)[0][0]
                logger.info(f"🎯 Auto-detected target version: {target_version}")
            else:
                target_version = "Auto-Detect"
            
            # Second pass: check each server and categorize
            for server in servers:
                try:
                    # Get version directly using _get_server_version (only takes server_ip)
                    version = self._get_server_version(server.get('ip'))
                    
                    if version and version != 'N/A' and version != 'Error' and version != 'Offline' and version != 'Unknown':
                        # Check if this version matches the target
                        if version == target_version:
                            successful_checks += 1
                            version_results.append({
                                'success': True,
                                'hostname': server.get('hostname', 'Unknown'),
                                'ip': server.get('ip', 'Unknown'),
                                'version': version,
                                'status': 'Found'
                            })
                            logger.info(f"✅ {server.get('hostname')}: {version}")
                        else:
                            # Different version found
                            failed_checks += 1
                            version_results.append({
                                'success': False,
                                'hostname': server.get('hostname', 'Unknown'),
                                'ip': server.get('ip', 'Unknown'),
                                'version': version,
                                'error': f'Different version (expected {target_version})',
                                'status': f'Different version: {version} (expected {target_version})'
                            })
                            logger.warning(f"⚠️ {server.get('hostname')}: Different version {version} (expected {target_version})")
                    else:
                        failed_checks += 1
                        version_results.append({
                            'success': False,
                            'hostname': server.get('hostname', 'Unknown'),
                            'ip': server.get('ip', 'Unknown'),
                            'version': version or 'N/A',
                            'error': 'Version not found or error',
                            'status': 'Error'
                        })
                        logger.warning(f"❌ {server.get('hostname')}: Version not found")
                except Exception as e:
                    failed_checks += 1
                    version_results.append({
                        'success': False,
                        'hostname': server.get('hostname', 'Unknown'),
                        'ip': server.get('ip', 'Unknown'),
                        'version': 'N/A',
                        'error': str(e),
                        'status': 'Error'
                    })
                    logger.error(f"❌ {server.get('hostname')}: {str(e)}")
            
            # Send email report (use the auto-detected target version)
            email_result = self.send_version_report_email(
                version_results, 
                successful_checks, 
                failed_checks, 
                target_version  # Use the most common version detected above
            )
            
            if email_result.get('status') == 'success':
                # Update last_run in config
                config["schedule"]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_email_config(config)
                
                # Send Lark notification
                success_rate = (successful_checks / len(version_results) * 100) if len(version_results) > 0 else 0
                lark_message = (
                    f"📧 **Version Check Email Sent**\n\n"
                    f"✅ Recipients: {len(recipients)}\n"
                    f"📊 Servers Checked: {len(version_results)}\n"
                    f"✅ Successful: {successful_checks}\n"
                    f"❌ Failed: {failed_checks}\n"
                    f"📈 Success Rate: {success_rate:.1f}%\n\n"
                    f"Email report has been sent to:\n{', '.join(recipients)}"
                )
                self._send_simple_lark_notification(lark_message)
                
                return {
                    "status": "success",
                    "message": f"Test version check completed. Email sent to {len(recipients)} recipients.",
                    "results": {
                        "total": len(version_results),
                        "successful": successful_checks,
                        "failed": failed_checks
                    }
                }
            else:
                # Send Lark notification for failure
                lark_message = (
                    f"❌ **Version Check Email Failed**\n\n"
                    f"📊 Servers Checked: {len(version_results)}\n"
                    f"✅ Successful: {successful_checks}\n"
                    f"❌ Failed: {failed_checks}\n\n"
                    f"Error: {email_result.get('message')}"
                )
                self._send_simple_lark_notification(lark_message)
                
                return {
                    "status": "error",
                    "message": f"Version check completed but email failed: {email_result.get('message')}"
                }
                
        except Exception as e:
            logger.error(f"❌ Error testing scheduled version check: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _send_simple_lark_notification(self, message: str):
        """Send a simple text notification to Lark webhook"""
        if not REQUESTS_AVAILABLE:
            return
        
        try:
            headers = {"Content-Type": "application/json; charset=utf-8"}
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Add timestamp to message
            full_message = f"📅 **Time:** {timestamp}\n\n{message}"
            
            # Prepare webhook body
            body = {
                "msg_type": "text",
                "content": {
                    "text": full_message
                }
            }
            
            # Send to Lark webhook
            logger.info(f"📤 Sending notification to Lark webhook...")
            response = requests.post(settings.LARK_WEBHOOK_URL, headers=headers, json=body, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Notification sent successfully to Lark")
            else:
                logger.error(f"❌ Failed to send notification to Lark webhook: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error sending Lark notification: {str(e)}")
    
    def send_version_report_email(self, version_results: List[Dict], successful_checks: int, 
                                   failed_checks: int, target_version: str) -> Dict:
        """Send version check report via email - matches Flask version"""
        try:
            # Hard-coded SMTP config matching Flask version
            smtp_server = "smtp.larksuite.com"
            smtp_port = 587
            sender_email = "osm@snsoft.my"
            sender_password = "xPuVkwARv4F5yiCW"
            
            # Get recipients from config file
            config = self.load_email_config()
            recipient_email = config.get("recipients", [])
            
            if not recipient_email:
                return {"status": "error", "message": "No recipients configured"}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipient_email)
            msg['Subject'] = f"Image Recon Version Check Report - {target_version} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Create email body
            total_servers = len(version_results)
            success_rate = (successful_checks / total_servers * 100) if total_servers > 0 else 0
            
            # Group results by status
            successful_results = [r for r in version_results if r.get('success', False)]
            different_version_results = [r for r in version_results if not r.get('success', False) and r.get('status', '').startswith('Different')]
            error_results = [r for r in version_results if not r.get('success', False) and not r.get('status', '').startswith('Different')]
            
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
                    .summary {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                    .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                    .stat {{ text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .stat.success {{ border-left: 4px solid #4CAF50; }}
                    .stat.warning {{ border-left: 4px solid #ff9800; }}
                    .stat.error {{ border-left: 4px solid #f44336; }}
                    .stat.info {{ border-left: 4px solid #2196F3; }}
                    .results {{ margin: 20px 0; }}
                    .result-section {{ margin: 20px 0; }}
                    .result-item {{ padding: 10px; margin: 5px 0; border-radius: 5px; }}
                    .result-item.success {{ background: rgba(76, 175, 80, 0.1); border-left: 4px solid #4CAF50; }}
                    .result-item.warning {{ background: rgba(255, 152, 0, 0.1); border-left: 4px solid #ff9800; }}
                    .result-item.error {{ background: rgba(244, 67, 54, 0.1); border-left: 4px solid #f44336; }}
                    .server-name {{ font-weight: bold; color: #2c3e50; }}
                    .version {{ font-family: monospace; background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔍 OSM Version Check Report</h1>
                    <p>Target Version: <span class="version">{target_version}</span></p>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="summary">
                    <h2>📊 Summary</h2>
                    <div class="stats">
                        <div class="stat success">
                            <h3>{successful_checks}</h3>
                            <p>Target Version Found</p>
                        </div>
                        <div class="stat warning">
                            <h3>{len(different_version_results)}</h3>
                            <p>Different Versions</p>
                        </div>
                        <div class="stat error">
                            <h3>{len(error_results)}</h3>
                            <p>Errors/Not Found</p>
                        </div>
                        <div class="stat info">
                            <h3>{total_servers}</h3>
                            <p>Total Servers</p>
                        </div>
                    </div>
                    <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
                </div>
                
                <div class="results">
                    {f'''
                    <div class="result-section">
                        <h3>✅ Servers with Target Version ({len(successful_results)})</h3>
                        {''.join([f'<div class="result-item success"><span class="server-name">{r["hostname"]}</span> ({r["ip"]}) - Version: <span class="version">{r["version"]}</span></div>' for r in successful_results])}
                    </div>
                    ''' if successful_results else ''}
                    
                    {f'''
                    <div class="result-section">
                        <h3>⚠️ Servers with Different Versions ({len(different_version_results)})</h3>
                        {''.join([f'<div class="result-item warning"><span class="server-name">{r["hostname"]}</span> ({r["ip"]}) - Found: <span class="version">{r["version"]}</span> | Status: {r.get("status", "Unknown")}</div>' for r in different_version_results])}
                    </div>
                    ''' if different_version_results else ''}
                    
                    {f'''
                    <div class="result-section">
                        <h3>❌ Servers with Issues ({len(error_results)})</h3>
                        {''.join([f'<div class="result-item error"><span class="server-name">{r["hostname"]}</span> ({r["ip"]}) - Version: <span class="version">{r.get("version", "N/A")}</span> | Error: {r.get("error", "Unknown error")}</div>' for r in error_results])}
                    </div>
                    ''' if error_results else ''}
                </div>
                
                <div style="margin-top: 30px; padding: 15px; background: #e3f2fd; border-radius: 8px; text-align: center;">
                    <p><em>This report was generated automatically by the OSM Tools Hub</em></p>
                </div>
            </body>
            </html>
            """
            
            # Attach HTML body
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            logger.info(f"📧 Sending version report email to {len(recipient_email)} recipients")
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipient_email, text)
            server.quit()
            
            logger.info(f"✅ Version report email sent successfully to {', '.join(recipient_email)}")
            return {"status": "success", "message": "Email sent successfully"}
            
        except Exception as e:
            logger.error(f"❌ Error sending version report email: {str(e)}")
            return {"status": "error", "message": str(e)}
    
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
                ip = server.get('ip', 'Unknown IP')  # Get the IP address
                ids = server.get('ids', [])
                
                # Search for the query in the ids list (case-insensitive)
                matching_ids = [id_obj['id'] for id_obj in ids if query_lower in id_obj['id'].lower()]
                
                if matching_ids:
                    matching_servers.append({
                        "hostname": hostname,
                        "ip": ip,  # Include IP address in results
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
        """Send batch email notifications - matches Flask version exactly"""
        try:
            # Hard-coded SMTP config matching Flask version
            smtp_server = "smtp.larksuite.com"
            smtp_port = 587
            sender_email = "osm@snsoft.my"
            sender_password = "xPuVkwARv4F5yiCW"
            
            # Get recipients from config file if not provided
            if not recipients:
                config = self.load_email_config()
                recipients = config.get("recipients", [])
            
            if not recipients:
                return {"status": "error", "message": "No recipients configured"}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject or f"OSM Tools Notification - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Build HTML email body matching Flask version
            if results:
                # Calculate statistics
                total_servers = len(results)
                successful_results = [r for r in results if r.get('success', False) or r.get('status', '').lower() == 'success']
                error_results = [r for r in results if not (r.get('success', False) or r.get('status', '').lower() == 'success')]
                success_rate = (len(successful_results) / total_servers * 100) if total_servers > 0 else 0
                
                html_body = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; text-align: center; }}
                        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                        .stat {{ text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                        .stat.success {{ border-left: 4px solid #4CAF50; }}
                        .stat.error {{ border-left: 4px solid #f44336; }}
                        .stat.info {{ border-left: 4px solid #2196F3; }}
                        .results {{ margin: 20px 0; }}
                        .result-section {{ margin: 20px 0; }}
                        .result-item {{ padding: 10px; margin: 5px 0; border-radius: 5px; }}
                        .result-item.success {{ background: rgba(76, 175, 80, 0.1); border-left: 4px solid #4CAF50; }}
                        .result-item.error {{ background: rgba(244, 67, 54, 0.1); border-left: 4px solid #f44336; }}
                        .server-name {{ font-weight: bold; color: #2c3e50; }}
                        .message {{ font-family: monospace; background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🔔 OSM Tools Notification</h1>
                        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <div class="summary">
                        <h2>📊 Summary</h2>
                        <div class="stats">
                            <div class="stat success">
                                <h3>{len(successful_results)}</h3>
                                <p>Successful</p>
                            </div>
                            <div class="stat error">
                                <h3>{len(error_results)}</h3>
                                <p>Failed</p>
                            </div>
                            <div class="stat info">
                                <h3>{total_servers}</h3>
                                <p>Total Servers</p>
                            </div>
                        </div>
                        <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
                    </div>
                    
                    <div class="results">
                        {f'''
                        <div class="result-section">
                            <h3>✅ Successful Operations ({len(successful_results)})</h3>
                            {''.join([f'<div class="result-item success"><span class="server-name">{r.get("hostname", r.get("ip", "Unknown"))}</span> - <span class="message">{r.get("message", "Success")}</span></div>' for r in successful_results])}
                        </div>
                        ''' if successful_results else ''}
                        
                        {f'''
                        <div class="result-section">
                            <h3>❌ Failed Operations ({len(error_results)})</h3>
                            {''.join([f'<div class="result-item error"><span class="server-name">{r.get("hostname", r.get("ip", "Unknown"))}</span> - <span class="message">{r.get("error", r.get("message", "Unknown error"))}</span></div>' for r in error_results])}
                        </div>
                        ''' if error_results else ''}
                    </div>
                    
                    {f'<div style="margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 8px;"><p><strong>Message:</strong> {message}</p></div>' if message else ''}
                    
                    <div style="margin-top: 30px; padding: 15px; background: #e3f2fd; border-radius: 8px; text-align: center;">
                        <p><em>This report was generated automatically by the OSM Tools Hub</em></p>
                    </div>
                </body>
                </html>
                """
                msg.attach(MIMEText(html_body, 'html'))
            else:
                # Simple text email
                msg.attach(MIMEText(message or "No content provided", 'plain'))
            
            # Send email
            logger.info(f"📧 Sending email to {len(recipients)} recipients via {smtp_server}")
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipients, text)
            server.quit()
            
            logger.info(f"✅ Email sent successfully to {', '.join(recipients)}")
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
            
            # Read server list from image-recon.json (returns a list of servers)
            servers_list = self.get_image_recon_servers()
            
            if not servers_list:
                return {"status": "error", "message": "No servers found in image-recon.json"}
            
            # Initialize the result data structure grouped by label
            refreshed_data = {}
            total_servers = 0
            successful_fetches = 0
            
            # Group servers by label and fetch IDs for each
            for server in servers_list:
                server_ip = server['ip']
                hostname = server['hostname']
                label = server.get('label', 'Unknown')
                total_servers += 1
                
                # Initialize label group if not exists
                if label not in refreshed_data:
                    refreshed_data[label] = []
                
                # Fetch the server IDs by SSH'ing into the server
                logger.info(f"📋 Fetching IDs from {hostname} ({server_ip})")
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
    
    def _analyze_server_status(self, logs: str, server_ip: str) -> Dict:
        """Analyze server logs to determine status - matches Flask 321123.py logic exactly"""
        # Check for specific offline indicators first (these take priority)
        offline_indicators = [
            "stopped osm service"
        ]
        
        is_offline = False
        for indicator in offline_indicators:
            if indicator in logs.lower():
                is_offline = True
                logger.warning(f"🔴 Server {server_ip} is OFFLINE (found: {indicator})")
                break
        
        # If we can't get logs at all due to connection issues, mark as offline
        if "Error:" in logs and any(indicator in logs.lower() for indicator in ["connection", "timeout", "ssh"]):
            is_offline = True
            logger.warning(f"🔴 Server {server_ip} is OFFLINE (connection error)")
        
        # Only check for application errors if server is not offline
        has_errors = False
        detected_error = None
        if not is_offline:
            # Look for specific application error keywords in logs (matches Flask exactly)
            error_indicators = [
                "exception caught: stoi",
                "system error",
                "segmentation fault",
                "cannot open connection",
                "core dumped",
                "aborted",
                "free(): invalid next size",
                "received signal 6",
                "curl handler not initialized"
            ]
            
            for indicator in error_indicators:
                if indicator in logs.lower():
                    has_errors = True
                    detected_error = indicator
                    logger.warning(f"🟡 Server {server_ip} has ERRORS (found: {indicator})")
                    break
        
        # Determine status color
        if is_offline:
            status_color = "black"
            status_text = "Offline"
        elif has_errors:
            status_color = "yellow"
            status_text = f"Error: {detected_error}"
        else:
            status_color = "green"
            status_text = "Online"
        
        return {
            "status_color": status_color,
            "status_text": status_text,
            "is_offline": is_offline,
            "has_errors": has_errors,
            "detected_error": detected_error
        }
    
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
