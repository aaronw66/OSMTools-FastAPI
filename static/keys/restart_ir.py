import json
import paramiko
import os
import logging
import time
from logging.handlers import RotatingFileHandler
from flask import Blueprint, render_template, jsonify, request, current_app
from datetime import datetime

# Create the blueprint for restart functionality
restart_ir_blueprint = Blueprint('restart_ir', __name__)

# =====================
# ✅ Dedicated Logging Setup for Restart IR
# =====================
def setup_restart_ir_logger():
    """Set up dedicated logger for Restart IR tool that doesn't interfere with other loggers"""
    # Use local path if server path doesn't exist
    SERVER_LOG_DIR = "/opt/compose-conf/web/log"
    LOCAL_LOG_DIR = "log"
    
    LOG_DIR = SERVER_LOG_DIR if os.path.exists(SERVER_LOG_DIR) else LOCAL_LOG_DIR
    LOG_FILE = os.path.join(LOG_DIR, "restart_ir.log")
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Create dedicated logger for Restart IR tool
    restart_logger = logging.getLogger('restart_ir')
    restart_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    if restart_logger.handlers:
        restart_logger.handlers.clear()
    
    # Create rotating file handler for Restart IR logs (max 10MB, keep 5 backup files)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [Restart-IR] %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    restart_logger.addHandler(file_handler)
    
    # Prevent logs from propagating to root logger (avoids duplication in auto.log)
    restart_logger.propagate = False
    
    return restart_logger

# Initialize the dedicated logger
logger = setup_restart_ir_logger()

# Log initialization message
logger.info("🚀 Restart IR logger initialized - logs will be stored in restart_ir.log")

# Route to render the restart_ir.html template
@restart_ir_blueprint.route('/restart-ir', methods=['GET'])
def show_restart_page():
    json_file_path = '/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json'

    try:
        # Read the JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Initialize server groups
        server_groups = {}

        # Ensure data is a list and process it
        if isinstance(data, list):
            for item in data:
                targets = item.get('targets', [])
                for target in targets:
                    ip = target.split(':')[0]
                    hostname = item.get('labels', {}).get('hostname', 'Unknown Host')

                    # Extract label (like 'DHS', 'NP', etc.)
                    label = hostname.split('-')[0]
                    
                    # Filter out SRS servers
                    if label.upper() == 'SRS':
                        logger.info(f"Filtering out SRS server: {hostname}")
                        continue
                    
                    if label not in server_groups:
                        server_groups[label] = []
                    server_groups[label].append({"hostname": hostname, "ip": ip})

        else:
            raise ValueError("The JSON structure is not a list")

        # Pass server_groups to the template for rendering
        return render_template('restart_ir.html', server_groups=server_groups)

    except Exception as e:
        logger.error(f"📂 Error loading server data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to fetch logs from the server
@restart_ir_blueprint.route('/get_logs', methods=['POST'])
def get_logs():
    server_ip = request.json.get('server_ip')  # Get server IP from the request

    if not server_ip:
        logger.error("🚫 Server IP is missing in the request.")
        return jsonify({"status": "error", "message": "Server IP is required"}), 400

    # Attempt to get logs from the server
    logs = get_logs_from_server(server_ip)

    if "Error" in logs:
        logger.error(f"📡 Error fetching logs for {server_ip}: {logs}")
        return jsonify({"status": "error", "message": logs}), 500

    return jsonify({"status": "success", "logs": logs}), 200


# Function to fetch logs from the server
def get_logs_from_server(server_ip):
    username = "ubuntu"  # Ensure this matches your SSH user
    private_key_filename = "image_identifier.pem"  # Ensure this is the correct private key

    private_key_path = os.path.join(current_app.root_path, 'static', 'keys', private_key_filename)

    try:
        # Confirm that the private key exists
        if not os.path.exists(private_key_path):
            raise ValueError(f"Private key file does not exist at path: {private_key_path}")

        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Load the private key for authentication
        private_key = paramiko.RSAKey.from_private_key_file(private_key_path)

        # Attempt SSH connection with a timeout
        ssh.connect(server_ip, username=username, pkey=private_key, timeout=60)

        # Run journalctl to fetch logs
        command = "journalctl -u osm -n 100"  # Fetch last 100 logs (No follow flag for now)
        logger.debug(f"Running command: {command}")

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
        logger.error(f"📡 Error fetching logs from {server_ip}: {str(e)}")
        return f"Error: {str(e)}"  # Return the error message as the logs

#Route to restart the application (service)
@restart_ir_blueprint.route('/restart_ir', methods=['POST'])
def restart_application():
    data = request.get_json()
    selected_server_ip = data.get('server_ip')

    if not selected_server_ip:
        logger.error("🚫 No server IP provided!")
        return jsonify({"status": "error", "message": "No server IP provided!"}), 400

    # Ensure IP address is passed correctly
    logger.info(f"🔄 Attempting to restart service on {selected_server_ip}.")

    username = "ubuntu"  # Ensure this matches your SSH user
    private_key_filename = "image_identifier.pem"  # Ensure this is the correct private key

    private_key_path = os.path.join(current_app.root_path, 'static', 'keys', private_key_filename)

    try:
        # Debugging: Confirm that the private key exists
        if not os.path.exists(private_key_path):
            raise ValueError(f"Private key file does not exist at path: {private_key_path}")
        
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Skip host key verification (for testing)

        # Load the private key for authentication
        private_key = paramiko.RSAKey.from_private_key_file(private_key_path)

        # Attempt SSH connection
        ssh.connect(selected_server_ip, username=username, pkey=private_key)

        # Log the restart attempt
        logger.info(f"✅ Successfully connected to {selected_server_ip}. Restarting service...")

        # Use sudo with systemctl to restart the service and verify it's running
        # The command: restart service, wait 10 seconds, then check if it's active
        restart_command = "echo 'your_sudo_password' | sudo -S systemctl restart osm && sleep 10 && systemctl is-active osm"

        # Execute the command with a longer timeout (3 minutes total)
        logger.info(f"⏱️ Executing restart command with 3-minute timeout...")
        stdin, stdout, stderr = ssh.exec_command(restart_command, timeout=180)

        # Wait for completion with timeout handling
        import time
        start_time = time.time()
        timeout = 180  # 3 minutes total timeout
        
        logger.info(f"⏳ Waiting for restart command to complete...")
        while not stdout.channel.exit_status_ready():
            if time.time() - start_time > timeout:
                ssh.close()
                logger.error(f"⏰ Restart timeout after {timeout} seconds on {selected_server_ip}")
                return jsonify({"status": "error", "message": f"Restart timeout after {timeout} seconds. Service may still be restarting."}), 500
            time.sleep(1)

        # Check if the restart was successful
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            # Read the service status output
            service_status = stdout.read().decode().strip()
            logger.info(f"📊 Service status after restart: {service_status}")
            
            if service_status == "active":
                ssh.close()
                logger.info(f"🎉 Service restarted successfully and is ACTIVE on {selected_server_ip}")
                return jsonify({"status": "success", "message": "Service restarted successfully and is now active."}), 200
            else:
                ssh.close()
                logger.warning(f"⚠️ Service restarted but status is '{service_status}' on {selected_server_ip}")
                return jsonify({"status": "warning", "message": f"Service restarted but current status is: {service_status}. Please check manually."}), 200
        else:
            ssh.close()
            error_message = stderr.read().decode()
            logger.error(f"💥 Error restarting service on {selected_server_ip}: {error_message}")
            return jsonify({"status": "error", "message": f"Failed to restart the service. {error_message}"}), 500

    except Exception as e:
        logger.error(f"Error: {e}")  # Detailed error message for debugging
        return jsonify({"status": "error", "message": str(e)}), 500

# Function to get server IDs from the list.json file on a remote server
def get_server_ids(ip):
    try:
        # SSH credentials and key file
        username = "ubuntu"
        private_key_filename = "image_identifier.pem"
        private_key_path = os.path.join(current_app.root_path, 'static', 'keys', private_key_filename)

        # Check if the private key exists
        if not os.path.exists(private_key_path):
            logger.error(f"Private key not found at: {private_key_path}")
            raise ValueError(f"Private key file does not exist at path: {private_key_path}")

        logger.info(f"🔌 Attempting to SSH into server {ip}")

        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Accept unknown host keys

        # Load private key
        private_key = paramiko.RSAKey.from_private_key_file(private_key_path)

        # Connect to the server
        ssh.connect(ip, username=username, pkey=private_key)

        logger.info(f"✅ Successfully connected to {ip}")

        # Run the command to fetch the ids from list.json
        command = "cat /usr/bin/OSMWatcher/list.json | grep -oP '\"id\": \"[^\"]+'"
        logger.info(f"🔍 Running command: {command}")

        stdin, stdout, stderr = ssh.exec_command(command)

        # Capture the results from stdout
        ids = stdout.read().decode()

        # Check if there were any results
        if not ids:
            logger.warning(f"⚠️ No IDs found for server {ip}")
            return []

        # Clean the results by removing extra characters and extracting the IDs
        cleaned_ids = [line.split(":")[1].strip().replace('"', '') for line in ids.splitlines()]

        # Prepare the cleaned IDs in the desired format
        id_objects = [{"id": id.strip()} for id in cleaned_ids]

        ssh.close()
        logger.info(f"📋 Fetched IDs for {ip}: {id_objects}")

        return id_objects

    except Exception as e:
        logger.error(f"📄 Error reading list.json from {ip}: {str(e)}")
        return []

# Function to read the server groups from the image-recon.json file
def read_server_groups():
    json_file_path = '/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json'
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Initialize server groups
        server_groups = {}

        # Ensure data is a list and process it
        if isinstance(data, list):
            for item in data:
                targets = item.get('targets', [])
                for target in targets:
                    ip = target.split(':')[0]  # Extract IP from target (before colon)
                    hostname = item.get('labels', {}).get('hostname', 'Unknown Host')

                    # Extract label (like 'DHS', 'NP', etc.)
                    label = hostname.split('-')[0]
                    
                    # Filter out SRS servers
                    if label.upper() == 'SRS':
                        logger.info(f"Filtering out SRS server: {hostname}")
                        continue
                    
                    if label not in server_groups:
                        server_groups[label] = []
                    server_groups[label].append({"hostname": hostname, "ip": ip})

        else:
            raise ValueError("The JSON structure is not a list")

        return server_groups

    except Exception as e:
        logger.error(f"Error reading server data: {str(e)}")
        return {}

# Function to refresh the server list and store it in ir.json
@restart_ir_blueprint.route('/refresh_servers', methods=['POST'])
def refresh_servers():
    try:
        # Read server groups from the image-recon.json file
        server_groups = read_server_groups()

        # Initialize the result data structure
        refreshed_data = {}

        # Loop through the servers and fetch the IDs for each server
        for label, servers in server_groups.items():
            refreshed_data[label] = []

            for server in servers:
                ip = server['ip']
                hostname = server['hostname']

                # Fetch the server IDs by SSH'ing into the server
                ids = get_server_ids(ip)

                if ids:
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
        json_file_path = '/opt/compose-conf/web/type/ir.json'

        # Check if the JSON file exists, if not create it
        if not os.path.exists(json_file_path):
            default_data = []
            with open(json_file_path, 'w') as f:
                json.dump(default_data, f)
            logger.info(f"📁 Created a new {json_file_path} with default data.")
        else:
            logger.info(f"📁 The {json_file_path} already exists.")

        # Write the refreshed server list to the JSON file
        with open(json_file_path, 'w') as f:
            json.dump(refreshed_data, f, indent=4)

        logger.info(f"🔄 Server list has been refreshed and written to {json_file_path}")

        # Invalidate cache after refresh
        global _server_data_cache, _cache_timestamp
        _server_data_cache = None
        _cache_timestamp = 0
        logger.info("🗑️ Cache invalidated after server refresh")

        # Respond with success message
        return jsonify({"status": "success", "message": "Server list refreshed successfully!"}), 200

    except Exception as e:
        # Log any error
        logger.error(f"🔄 Error refreshing server list: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Cache for server data to improve search performance
_server_data_cache = None
_cache_timestamp = 0
CACHE_DURATION = 300  # Cache for 5 minutes

# Search request counter to prevent overwhelming the server
_search_request_count = 0
_last_search_time = 0
SEARCH_COOLDOWN = 1  # Minimum 1 second between searches

def get_cached_server_data():
    """Get server data from cache or load from file if cache is expired"""
    global _server_data_cache, _cache_timestamp
    current_time = time.time()
    
    if (_server_data_cache is None or 
        current_time - _cache_timestamp > CACHE_DURATION):
        logger.info("🔄 Loading server data from file (cache expired)")
        file_start = time.time()
        _server_data_cache = read_server_groups_from_ir_json()
        file_time = time.time() - file_start
        logger.info(f"📁 File read took: {file_time:.3f} seconds")
        _cache_timestamp = current_time
    else:
        logger.info("⚡ Using cached server data")
    
    return _server_data_cache

# Function to search for machines in the ir.json file
@restart_ir_blueprint.route('/search_machines', methods=['POST'])
def search_machines():
    global _search_request_count, _last_search_time
    
    # Rate limiting to prevent overwhelming the server
    current_time = time.time()
    if current_time - _last_search_time < SEARCH_COOLDOWN:
        logger.warning(f"🚫 Search rate limited: too many requests")
        return jsonify({"status": "error", "message": "Please wait before searching again."}), 429
    
    _last_search_time = current_time
    _search_request_count += 1
    
    start_time = time.time()
    query = request.json.get('query')  # The search query (e.g., '2133')

    # Debugging: Log the incoming query
    logger.info(f"🔍 Received search query: {query} (request #{_search_request_count})")

    if not query:
        return jsonify({"status": "error", "message": "Query parameter is required."}), 400
    
    # Get server data from cache
    cache_start = time.time()
    server_groups = get_cached_server_data()
    cache_time = time.time() - cache_start
    logger.info(f"⚡ Cache lookup took: {cache_time:.3f} seconds")

    # If no server groups were found, return error
    if not server_groups:
        return jsonify({"status": "error", "message": "No servers available to search."}), 500

    matching_servers = []
    query_lower = query.lower()  # Case-insensitive search

    # Optimized search: stop after finding first few matches
    search_start = time.time()
    max_results = 5  # Limit results for faster response
    
    for label, servers in server_groups.items():
        if len(matching_servers) >= max_results:
            break
            
        for server in servers:
            if len(matching_servers) >= max_results:
                break
                
            hostname = server['hostname']
            ids = server.get('ids', [])
            
            # Search for the query in the ids list (case-insensitive)
            matching_ids = [id_obj['id'] for id_obj in ids if query_lower in id_obj['id'].lower()]

            if matching_ids:
                matching_servers.append({
                    "hostname": hostname,
                    "matching_ids": matching_ids
                })

    search_time = time.time() - search_start
    total_time = time.time() - start_time
    logger.info(f"🔍 Search completed: Found {len(matching_servers)} matching servers in {search_time:.3f}s (total: {total_time:.3f}s)")

    # Return the matching servers and their IDs
    if matching_servers:
        return jsonify({"status": "success", "servers": matching_servers}), 200
    else:
        return jsonify({"status": "error", "message": "No machines found matching the query."}), 404

# Function to read the server groups from the ir.json file
def read_server_groups_from_ir_json():
    json_file_path = '/opt/compose-conf/web/type/ir.json'

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Initialize server groups
        server_groups = {}

        # Ensure data is a dictionary with labels as keys and lists as values
        if isinstance(data, dict):
            for label, servers in data.items():
                server_groups[label] = []
                for server in servers:
                    hostname = server.get('hostname', 'Unknown Host')
                    ids = server.get('ids', [])
                    server_groups[label].append({
                        "hostname": hostname,
                        "ids": ids
                    })

        else:
            raise ValueError("The JSON structure is not a dictionary")

        return server_groups

    except Exception as e:
        logger.error(f"📄 Error reading server data from ir.json: {str(e)}")
        return {}

# Global variables to track update progress
update_progress = {
    'is_running': False,
    'current_server': 0,
    'total_servers': 0,
    'successful_updates': 0,
    'failed_updates': 0,
    'ignored_count': 0,
    'current_server_ip': '',
    'current_server_hostname': '',
    'successful_servers': [],
    'failed_servers': [],
    'start_time': None
}

# Function to start update process (non-blocking)
@restart_ir_blueprint.route('/start_update_process', methods=['POST'])
def start_update_process():
    global update_progress
    
    if update_progress['is_running']:
        return jsonify({"status": "error", "message": "Update process is already running"}), 400
    
    try:
        # Configuration
        JSON_FILE = "/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json"
        KEY_FILE = "image_identifier.pem"
        IGNORE_IPS = ["10.50.14.119"]  # IPs to skip during update
        
        # Load server IPs from JSON
        try:
            with open(JSON_FILE, 'r') as file:
                data = json.load(file)
                
            # Extract IPs from the specific structure: data[].labels.instance
            all_server_ips = []
            for i, item in enumerate(data):
                if isinstance(item, dict) and 'labels' in item:
                    labels = item['labels']
                    if isinstance(labels, dict) and 'instance' in labels:
                        ip = labels['instance']
                        hostname = labels.get('hostname', 'Unknown')
                        all_server_ips.append({'ip': ip, 'hostname': hostname})
                        
        except Exception as e:
            logger.error(f"❌ Error reading server configuration: {str(e)}")
            return jsonify({"status": "error", "message": f"Failed to read server configuration: {str(e)}"}), 500
        
        if not all_server_ips:
            return jsonify({"status": "error", "message": "No server IPs found in configuration"}), 500
        
        # Filter out ignored IPs
        server_ips = [server for server in all_server_ips if server['ip'] not in IGNORE_IPS]
        ignored_count = len(all_server_ips) - len(server_ips)
        
        # Initialize progress
        update_progress.update({
            'is_running': True,
            'current_server': 0,
            'total_servers': len(server_ips),
            'successful_updates': 0,
            'failed_updates': 0,
            'ignored_count': ignored_count,
            'successful_servers': [],
            'failed_servers': [],
            'start_time': time.time()
        })
        
        logger.info(f"🚀 Starting background update process for {len(server_ips)} servers")
        
        # Start background thread
        import threading
        update_thread = threading.Thread(target=run_update_process, args=(server_ips, data))
        update_thread.daemon = True
        update_thread.start()
        
        return jsonify({
            "status": "success", 
            "message": f"Update process started for {len(server_ips)} servers",
            "total_servers": len(server_ips),
            "ignored_count": ignored_count
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error starting update process: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Function to get update progress
@restart_ir_blueprint.route('/get_update_progress', methods=['GET'])
def get_update_progress():
    global update_progress
    
    if not update_progress['is_running']:
        return jsonify({"status": "not_running"}), 200
    
    # Calculate progress percentage
    progress_percent = (update_progress['current_server'] / update_progress['total_servers']) * 100 if update_progress['total_servers'] > 0 else 0
    
    # Calculate estimated time remaining
    if update_progress['start_time'] and update_progress['current_server'] > 0:
        elapsed_time = time.time() - update_progress['start_time']
        avg_time_per_server = elapsed_time / update_progress['current_server']
        remaining_servers = update_progress['total_servers'] - update_progress['current_server']
        estimated_remaining = avg_time_per_server * remaining_servers
    else:
        estimated_remaining = None
    
    return jsonify({
        "status": "running",
        "progress_percent": round(progress_percent, 1),
        "current_server": update_progress['current_server'],
        "total_servers": update_progress['total_servers'],
        "successful_updates": update_progress['successful_updates'],
        "failed_updates": update_progress['failed_updates'],
        "ignored_count": update_progress['ignored_count'],
        "current_server_ip": update_progress['current_server_ip'],
        "current_server_hostname": update_progress['current_server_hostname'],
        "start_time": update_progress['start_time'],
        "estimated_remaining": estimated_remaining
    }), 200

# Function to get final update results
@restart_ir_blueprint.route('/get_update_results', methods=['GET'])
def get_update_results():
    global update_progress
    
    if update_progress['is_running']:
        return jsonify({"status": "still_running", "message": "Update process is still running"}), 200
    
    return jsonify({
        "status": "completed",
        "successful_updates": update_progress['successful_updates'],
        "failed_updates": update_progress['failed_updates'],
        "ignored_count": update_progress['ignored_count'],
        "total_servers": update_progress['total_servers'],
        "successful_servers": update_progress['successful_servers'],
        "failed_servers": update_progress['failed_servers']
    }), 200

# Background function to run the update process
def run_update_process(server_ips, data):
    global update_progress
    
    try:
        for i, server_info in enumerate(server_ips, 1):
            ip = server_info['ip']
            hostname = server_info['hostname']
            
            # Update progress
            update_progress.update({
                'current_server': i,
                'current_server_ip': ip,
                'current_server_hostname': hostname
            })
            
            logger.info(f"🔄 Processing server {i}/{len(server_ips)}: {ip} ({hostname})")
            
            update_result = update_single_server(ip)
            if update_result['success']:
                update_progress['successful_updates'] += 1
                update_progress['successful_servers'].append({
                    'ip': ip,
                    'hostname': hostname,
                    'status': 'success'
                })
                logger.info(f"✅ Successfully updated server {ip} ({hostname})")
            else:
                update_progress['failed_updates'] += 1
                update_progress['failed_servers'].append({
                    'ip': ip,
                    'hostname': hostname,
                    'status': 'failed',
                    'error': update_result['error']
                })
                logger.error(f"❌ Failed to update server {ip} ({hostname}): {update_result['error']}")
            
            # Small delay between servers
            if i < len(server_ips):
                logger.info(f"⏳ Waiting 10 seconds before next server...")
                time.sleep(10)
        
        # Mark as completed
        update_progress['is_running'] = False
        logger.info(f"📊 UPDATE SUMMARY - Successful: {update_progress['successful_updates']}, Failed: {update_progress['failed_updates']}, Ignored: {update_progress['ignored_count']}")
        
    except Exception as e:
        logger.error(f"❌ Error in background update process: {str(e)}")
        update_progress['is_running'] = False

# Legacy route for backward compatibility (now starts background process)
@restart_ir_blueprint.route('/update_all_servers', methods=['POST'])
def update_all_servers():
    return start_update_process()

def update_single_server(ip):
    """Update a single server with the latest Image Recognition version."""
    username = "ubuntu"
    private_key_filename = "image_identifier.pem"
    private_key_path = os.path.join(current_app.root_path, 'static', 'keys', private_key_filename)
    
    try:
        # Check if the private key exists
        if not os.path.exists(private_key_path):
            error_msg = f"Private key not found at: {private_key_path}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load the private key for authentication
        private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
        
        # Attempt SSH connection
        try:
            ssh.connect(ip, username=username, pkey=private_key, timeout=60)
            logger.info(f"✅ Successfully connected to {ip}")
        except Exception as e:
            error_msg = f"SSH connection failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Step 1: Check if update script exists
        logger.info(f"🔍 Checking if update script exists on {ip}...")
        check_cmd = "sudo ls -la /bak/bin/update_image_recon.sh"
        stdin, stdout, stderr = ssh.exec_command(check_cmd, timeout=30)
        
        if stdout.channel.recv_exit_status() != 0:
            error_msg = "Update script not found: /bak/bin/update_image_recon.sh"
            logger.error(f"❌ {error_msg}")
            ssh.close()
            return {"success": False, "error": error_msg}
        
        # Step 2: Run the update script
        logger.info(f"🔄 Running update script on {ip}...")
        update_cmd = "sudo bash /bak/bin/update_image_recon.sh"
        stdin, stdout, stderr = ssh.exec_command(update_cmd, timeout=600)  # 10 minute timeout
        
        # Wait for completion
        start_time = time.time()
        timeout = 600
        
        while not stdout.channel.exit_status_ready():
            if time.time() - start_time > timeout:
                error_msg = "Update script timeout after 10 minutes"
                logger.error(f"⏰ {error_msg}")
                ssh.close()
                return {"success": False, "error": error_msg}
            time.sleep(1)
        
        if stdout.channel.recv_exit_status() != 0:
            error_message = stderr.read().decode()
            error_msg = f"Update script failed: {error_message}"
            logger.error(f"❌ {error_msg}")
            ssh.close()
            return {"success": False, "error": error_msg}
        
        # Step 3: Check version in logs
        logger.info(f"🔍 Checking version in logs on {ip}...")
        version_cmd = 'sudo grep "3.1.2306-1" /usr/bin/OSMWatcher/logs/* 2>/dev/null || echo "Version not found in logs"'
        stdin, stdout, stderr = ssh.exec_command(version_cmd, timeout=30)
        
        version_output = stdout.read().decode().strip()
        if "Version not found in logs" not in version_output:
            logger.info(f"✅ Version 3.1.2306-1 found in logs on {ip}")
        else:
            logger.warning(f"⚠️ Version 3.1.2306-1 not found in logs on {ip}")
        
        # Step 4: Check OSM service status
        logger.info(f"🔍 Checking OSM service status on {ip}...")
        status_cmd = "sudo systemctl status osm --no-pager"
        stdin, stdout, stderr = ssh.exec_command(status_cmd, timeout=30)
        
        if stdout.channel.recv_exit_status() == 0:
            output = stdout.read().decode().lower()
            if 'active (running)' in output:
                logger.info(f"✅ OSM service is active and running on {ip}")
            else:
                logger.warning(f"⚠️ OSM service status unclear on {ip}")
        else:
            error_msg = "Failed to check OSM service status"
            logger.error(f"❌ {error_msg}")
            ssh.close()
            return {"success": False, "error": error_msg}
        
        ssh.close()
        logger.info(f"✅ All update steps completed successfully for {ip}")
        return {"success": True, "error": None}
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

# Route to check server status
@restart_ir_blueprint.route('/check_server_status', methods=['POST'])
def check_server_status():
    data = request.get_json()
    server_ip = data.get('server_ip')
    
    if not server_ip:
        return jsonify({"status": "error", "message": "Server IP is required"}), 400
    
    try:
        # Get logs from server to check status
        logs = get_logs_from_server(server_ip)
        
        # Check for specific offline indicators first (these take priority)
        offline_indicators = [
            "stopped osm service"
        ]
        
        is_offline = False
        for indicator in offline_indicators:
            if indicator in logs.lower():
                is_offline = True
                break
        
        # If we can't get logs at all due to connection issues, mark as offline
        if "Error:" in logs and any(indicator in logs.lower() for indicator in ["connection", "timeout", "ssh"]):
            is_offline = True
        
        # Only check for application errors if server is not offline
        has_errors = False
        if not is_offline:
            # Look for specific application error keywords in logs
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
                    logger.info(f"Found error indicator '{indicator}' in logs for {server_ip}")
                    break
        
        # Only log if there are issues
        if is_offline or has_errors:
            if is_offline:
                logger.warning(f"🔴 Server {server_ip} is OFFLINE")
            elif has_errors:
                logger.warning(f"⚠️ Server {server_ip} has ERRORS")
        
        return jsonify({
            "status": "success",
            "is_offline": is_offline,
            "has_errors": has_errors,
            "server_ip": server_ip
        })
        
    except Exception as e:
        logger.error(f"❌ Error checking status for {server_ip}: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "is_offline": True,
            "has_errors": False  # Changed to False since it's a connection issue
        }), 500

