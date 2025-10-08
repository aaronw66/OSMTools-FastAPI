import os
import logging
import socket
import paramiko
from typing import Dict, List, Optional
from datetime import datetime
from lxml import etree
from concurrent import futures
from logging.handlers import RotatingFileHandler

# Setup dedicated logger
def setup_osmachine_logger():
    """Set up dedicated logger for OSMachine tool"""
    LOG_DIR = "./logs"
    LOG_FILE = os.path.join(LOG_DIR, "osmachine.log")
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger('osmachine')
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        logger.handlers.clear()
    
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [OSMachine] %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.propagate = False
    
    return logger

logger = setup_osmachine_logger()

# SSH Configuration
SSH_CONFIG = {
    'username': 'root',
    'port': 28232,
    'password': 'cq4Q&0*20rCt',
    'timeout': 30,
    'connect_timeout': 5
}

# Path to lognavigator.xml
REMOTE_LOGNAV_DIR = "/opt/compose-conf/lognavigator"
REMOTE_LOGNAV_FILE = os.path.join(REMOTE_LOGNAV_DIR, 'lognavigator.xml')
LOCAL_CACHE_DIR = "./config/lognavigator"
LOCAL_CACHE_FILE = os.path.join(LOCAL_CACHE_DIR, 'lognavigator.xml')

# Allowed groups for machine restart functionality
ALLOWED_GROUPS = [
    'OSM_CP',
    'OSM_TBP',
    'OSM_TBR',
    'OSM_WF',
    'OSM_NCH',
    'OSM_DHS',
    'OSM_MDR',
    'OSM_NP',
    'OSM_LUCKYLINK',
    'LUCKYLINK_NCH'
]

# Group categorization
GROUP_CATEGORIES = {
    'OSM Production': [
        'OSM_CP',
        'OSM_TBP', 
        'OSM_TBR',
        'OSM_WF',
        'OSM_NCH',
        'OSM_DHS'
    ],
    'Gaming Platforms': [
        'OSM_MDR',
        'OSM_LUCKYLINK',
        'LUCKYLINK_NCH'
    ],
    'Regional Sites': [
        'OSM_NP'
    ]
}

# Operation modes
OPERATION_MODES = {
    'soft_restart': {
        'name': 'Soft Restart',
        'description': 'Graceful restart of services',
        'command': 'cd /home/pi/osm && ./stopallserver.sh && ./startallserver.sh',
        'icon': '🔄'
    },
    'hard_restart': {
        'name': 'Hard Restart',
        'description': 'Force restart of services',
        'command': 'cd /home/pi/osm && ./stopallserver.sh && sleep 5 && ./startallserver.sh',
        'icon': '⚡'
    },
    'full_reboot': {
        'name': 'Full Reboot',
        'description': 'Complete system reboot',
        'command': 'reboot',
        'icon': '🖥️'
    }
}

class OSMachineService:
    def __init__(self):
        self.logger = logger
        self.logger.info("🚀 OSMachine service initialized")
    
    def is_group_allowed(self, group_name: str) -> bool:
        """Check if a group is in the allowed list"""
        return group_name in ALLOWED_GROUPS
    
    def get_group_category(self, group_name: str) -> str:
        """Get the category for a given group"""
        for category, groups in GROUP_CATEGORIES.items():
            if group_name in groups:
                return category
        return 'Uncategorized'
    
    def organize_machines_by_category(self, machines: Dict) -> Dict:
        """Organize machines by logical categories"""
        categorized_machines = {}
        
        for group_name, group_machines in machines.items():
            category = self.get_group_category(group_name)
            
            if category not in categorized_machines:
                categorized_machines[category] = {}
            
            categorized_machines[category][group_name] = group_machines
        
        return categorized_machines
    
    def fetch_xml_from_filesystem(self) -> Optional[str]:
        """Fetch lognavigator.xml from local filesystem"""
        try:
            possible_paths = [
                REMOTE_LOGNAV_FILE,
                "/compose-conf/lognavigator/lognavigator.xml",
                "/opt/compose-conf/web/config/lognavigator/lognavigator.xml",
                "/var/log/lognavigator/lognavigator.xml",
                "/etc/lognavigator/lognavigator.xml"
            ]
            
            self.logger.info("🔍 Attempting to read lognavigator.xml from local filesystem")
            
            for file_path in possible_paths:
                if os.path.exists(file_path):
                    self.logger.info(f"✅ Found XML file at: {file_path}")
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    
                    if xml_content:
                        xml_size = len(xml_content)
                        self.logger.info(f"✅ Successfully read lognavigator.xml ({xml_size} bytes)")
                        machine_count = xml_content.count('<log-access-config')
                        self.logger.info(f"🔢 Found approximately {machine_count} machine entries in XML")
                        return xml_content
                    else:
                        self.logger.warning(f"⚠️ File exists but is empty: {file_path}")
            
            self.logger.error("❌ XML file not found in any of the expected locations")
            return None
                
        except Exception as e:
            self.logger.error(f"❌ Failed to read XML from filesystem: {str(e)}")
            return None
    
    def read_machines_from_lognavigator(self, force_remote: bool = False) -> Dict:
        """Read machine IPs and configurations from lognavigator.xml with filtering"""
        try:
            self.logger.info(f"🔍 Starting read_machines_from_lognavigator (force_remote={force_remote})")
            
            xml_content = None
            if not force_remote and os.path.exists(LOCAL_CACHE_FILE):
                try:
                    with open(LOCAL_CACHE_FILE, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    self.logger.info(f"📋 Using cached lognavigator.xml from: {LOCAL_CACHE_FILE}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to read cached XML: {str(e)}")
            
            if not xml_content:
                self.logger.info(f"🔄 Fetching lognavigator.xml from filesystem: {REMOTE_LOGNAV_FILE}")
                xml_content = self.fetch_xml_from_filesystem()
                
                if not xml_content:
                    self.logger.error("❌ Failed to fetch lognavigator.xml")
                    return {}
                
                # Cache the XML content
                try:
                    os.makedirs(LOCAL_CACHE_DIR, exist_ok=True)
                    with open(LOCAL_CACHE_FILE, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    self.logger.info(f"💾 Cached lognavigator.xml to: {LOCAL_CACHE_FILE}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to cache XML: {str(e)}")
            
            # Parse the XML content
            self.logger.info(f"🔍 Parsing XML content ({len(xml_content)} bytes)")
            try:
                root = etree.fromstring(xml_content.encode('utf-8'))
            except Exception as xml_parse_error:
                self.logger.error(f"❌ Failed to parse XML content: {str(xml_parse_error)}")
                return {}
            
            machines = {}
            total_machines = 0
            filtered_machines = 0
            all_groups_found = set()
            
            # Find all log-access-config elements
            for config in root.findall('.//log-access-config'):
                config_id = config.get('id', 'Unknown')
                url = config.get('url', '')
                
                # Try different attribute names for display group
                display_group = config.get('display-group', None)
                if not display_group:
                    display_group = config.get('displayGroup', None)
                if not display_group:
                    display_group = config.get('display_group', None)
                if not display_group:
                    display_group = 'Unknown'
                
                # Track all groups found for debugging
                if display_group != 'Unknown':
                    all_groups_found.add(display_group)
                
                total_machines += 1
                
                # Debug: Log first 3 machines to see what we're getting
                if total_machines <= 3:
                    self.logger.info(f"📋 Sample machine {total_machines}: config_id={config_id}, display_group={display_group}, url={url}")
                
                # Filter: Only include machines from allowed groups
                if not self.is_group_allowed(display_group):
                    continue
                
                filtered_machines += 1
                
                # Extract IP from URL
                ip = url.replace('http://', '').replace('https://', '').replace(':80', '').replace(':443', '')
                if ':' in ip:
                    ip = ip.split(':')[0]
                
                # Debug: Log if IP extraction failed
                if not ip or ip == 'Unknown':
                    self.logger.warning(f"⚠️ Skipping machine {config_id} in group {display_group} - invalid IP from URL: {url}")
                    continue
                
                if display_group not in machines:
                    machines[display_group] = []
                
                machines[display_group].append({
                    'ip': ip,
                    'config_id': config_id,
                    'display_group': display_group,
                    'url': url,
                    'status': 'unknown'
                })
            
            self.logger.info(f"📋 Machine filtering results:")
            self.logger.info(f"   - Total machines in XML: {total_machines}")
            self.logger.info(f"   - Filtered machines (allowed): {filtered_machines}")
            self.logger.info(f"   - Excluded machines: {total_machines - filtered_machines}")
            self.logger.info(f"   - All unique groups found in XML: {sorted(list(all_groups_found))}")
            self.logger.info(f"   - Allowed groups configured: {ALLOWED_GROUPS}")
            self.logger.info(f"   - Allowed groups found: {list(machines.keys())}")
            self.logger.info(f"   - Total machines added to result: {sum(len(m) for m in machines.values())}")
            
            if not machines:
                self.logger.error("❌ No machines found after filtering! Check if allowed groups match XML groups.")
            
            return machines
            
        except Exception as e:
            self.logger.error(f"❌ Error reading lognavigator.xml: {str(e)}")
            return {}
    
    def check_machine_status_fast(self, ip: str, timeout: int = 3) -> str:
        """Fast status check with shorter timeout for bulk operations"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                ip, 
                port=SSH_CONFIG['port'], 
                username=SSH_CONFIG['username'], 
                password=SSH_CONFIG['password'],
                timeout=timeout,
                banner_timeout=timeout
            )
            
            stdin, stdout, stderr = ssh.exec_command('echo "test"', timeout=2)
            exit_status = stdout.channel.recv_exit_status()
            
            ssh.close()
            return 'online' if exit_status == 0 else 'offline'
            
        except socket.timeout:
            return 'error'
        except Exception:
            return 'error'
    
    def check_machine_status(self, ip: str) -> tuple:
        """Check if a machine is online by attempting SSH connection"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            socket.setdefaulttimeout(SSH_CONFIG['connect_timeout'])
            
            ssh.connect(
                ip, 
                port=SSH_CONFIG['port'], 
                username=SSH_CONFIG['username'], 
                password=SSH_CONFIG['password'],
                timeout=SSH_CONFIG['connect_timeout'],
                banner_timeout=SSH_CONFIG['connect_timeout'],
                auth_timeout=SSH_CONFIG['connect_timeout']
            )
            
            stdin, stdout, stderr = ssh.exec_command('echo "test"', timeout=5)
            exit_status = stdout.channel.recv_exit_status()
            
            ssh.close()
            
            if exit_status == 0:
                return True, "Online"
            else:
                return False, "Connection failed"
                
        except socket.timeout:
            return False, "Connection timeout"
        except paramiko.AuthenticationException:
            return False, "Authentication failed"
        except paramiko.SSHException as e:
            return False, f"SSH error: {str(e)[:50]}"
        except Exception as e:
            error_msg = str(e)[:50]
            if "timed out" in error_msg.lower():
                return False, "Connection timeout"
            return False, f"Error: {error_msg}"
    
    def batch_check_status(self, machines: List[Dict], max_concurrent: int = 20) -> Dict:
        """Check status of multiple machines concurrently"""
        from threading import Lock
        
        results = {}
        lock = Lock()
        
        def check_single_machine(machine):
            ip = machine['ip']
            try:
                status = self.check_machine_status_fast(ip)
            except Exception:
                status = 'error'
            
            with lock:
                results[ip] = {
                    'ip': ip,
                    'config_id': machine['config_id'],
                    'display_group': machine['display_group'],
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                }
        
        with futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_list = [executor.submit(check_single_machine, machine) for machine in machines]
            futures.wait(future_list)
        
        return results
    
    def restart_machine(self, ip: str, operation_mode: str = 'soft_restart') -> tuple:
        """Restart a machine via SSH with different operation modes"""
        try:
            if operation_mode not in OPERATION_MODES:
                self.logger.error(f"❌ Invalid operation mode: {operation_mode}")
                return False, f"Invalid operation mode: {operation_mode}"
            
            mode_info = OPERATION_MODES[operation_mode]
            self.logger.info(f"{mode_info['icon']} Attempting {mode_info['name']} on machine: {ip}")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                ip, 
                port=SSH_CONFIG['port'], 
                username=SSH_CONFIG['username'], 
                password=SSH_CONFIG['password'],
                timeout=SSH_CONFIG['timeout']
            )
            
            command = mode_info['command']
            stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
            
            exit_status = stdout.channel.recv_exit_status()
            error_output = stderr.read().decode('utf-8', errors='ignore')
            
            ssh.close()
            
            if exit_status == 0:
                self.logger.info(f"✅ Successfully initiated {mode_info['name']} for machine: {ip}")
                return True, f"{mode_info['name']} command sent successfully"
            else:
                self.logger.error(f"❌ Failed to {mode_info['name'].lower()} machine {ip}: {error_output}")
                return False, f"{mode_info['name']} failed: {error_output}"
                
        except Exception as e:
            self.logger.error(f"❌ Error {operation_mode} on machine {ip}: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def get_machine_logs(self, ip: str, date: str = None, lines: int = 100) -> Dict:
        """Get logs from a specific machine"""
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Validate date format
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return {
                    "status": "error",
                    "message": "Invalid date format. Use YYYY-MM-DD"
                }
            
            log_file = f"/home/pi/osm/logs/logic/{date}.log"
            
            self.logger.info(f"📋 Fetching logs from {ip}:{log_file} (last {lines} lines)")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                ip, 
                port=SSH_CONFIG['port'], 
                username=SSH_CONFIG['username'], 
                password=SSH_CONFIG['password'],
                timeout=SSH_CONFIG['timeout']
            )
            
            # Check if log file exists
            stdin, stdout, stderr = ssh.exec_command(f'test -f "{log_file}" && test -s "{log_file}" && echo "exists" || echo "not_found"')
            file_exists = stdout.read().decode().strip()
            
            if file_exists == "not_found":
                ssh.close()
                return {
                    "status": "error",
                    "message": f"Log file not found or is empty: {log_file}"
                }
            
            # Get the last N lines
            command = f'tail -n {lines} "{log_file}"'
            stdin, stdout, stderr = ssh.exec_command(command)
            
            log_content = stdout.read().decode('utf-8', errors='ignore')
            
            # Get file info
            stdin, stdout, stderr = ssh.exec_command(f'wc -l "{log_file}"')
            wc_output = stdout.read().decode().strip()
            total_lines = wc_output.split()[0] if wc_output else "0"
            
            stdin, stdout, stderr = ssh.exec_command(f'ls -lh "{log_file}"')
            file_info = stdout.read().decode().strip()
            
            ssh.close()
            
            return {
                "status": "success",
                "ip": ip,
                "date": date,
                "log_file": log_file,
                "content": log_content,
                "lines_fetched": len(log_content.splitlines()),
                "total_lines": total_lines,
                "file_info": file_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting logs from {ip}: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def refresh_machines(self) -> Dict:
        """Refresh machine list by removing cache and re-reading XML"""
        try:
            if os.path.exists(LOCAL_CACHE_FILE):
                try:
                    os.remove(LOCAL_CACHE_FILE)
                    self.logger.info("🗑️ Removed local XML cache to force refresh")
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to remove cache: {str(e)}")
            
            self.logger.info("🔄 Forcing remote fetch of lognavigator.xml")
            machines = self.read_machines_from_lognavigator(force_remote=True)
            
            if not machines:
                return {
                    "status": "error",
                    "message": "No machines found in allowed groups from lognavigator.xml"
                }
            
            total_machines = sum(len(machines[group]) for group in machines)
            self.logger.info(f"🔄 Machine list refreshed: {total_machines} machines from {len(machines)} allowed groups found")
            
            return {
                "status": "success",
                "message": f"Machine list refreshed successfully. Found {total_machines} machines from {len(machines)} allowed groups.",
                "machines": machines
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error refreshing machine list: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_operation_modes(self) -> Dict:
        """Get available operation modes"""
        return OPERATION_MODES
    
    def get_allowed_groups_info(self) -> Dict:
        """Get information about allowed groups configuration"""
        return {
            'allowed_groups': ALLOWED_GROUPS,
            'total_allowed': len(ALLOWED_GROUPS),
            'group_categories': GROUP_CATEGORIES
        }
