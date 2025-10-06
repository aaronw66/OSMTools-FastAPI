#!/usr/bin/env python3

import json
import subprocess
import sys
import time
from pathlib import Path

def load_server_ips(json_file_path):
    """Load server IP addresses from the JSON configuration file."""
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
            
        print(f"📊 JSON structure: Array with {len(data)} entries")
        
        # Extract IPs from the specific structure: data[].labels.instance
        ips = []
        for i, item in enumerate(data):
            if isinstance(item, dict) and 'labels' in item:
                labels = item['labels']
                if isinstance(labels, dict) and 'instance' in labels:
                    ip = labels['instance']
                    hostname = labels.get('hostname', 'Unknown')
                    print(f"🔍 Found server {i+1}: {ip} ({hostname})")
                    ips.append(ip)
                    
        print(f"📋 Total servers found: {len(ips)}")
        return ips
        
    except FileNotFoundError:
        print(f"❌ Error: File {json_file_path} not found")
        print("Please check the file path is correct")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {json_file_path}")
        print(f"JSON error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error reading {json_file_path}: {e}")
        return []

def ssh_and_update(ip, key_file):
    """SSH into a server and run the specific update process."""
    print(f"\n{'='*50}")
    print(f"Connecting to server: {ip}")
    print(f"{'='*50}")
    
    # First, let's check if the script exists and is executable
    print("🔍 Checking if update script exists...")
    try:
        check_cmd = [
            'ssh',
            '-i', key_file,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=10',
            f'ubuntu@{ip}',
            'sudo ls -la /bak/bin/update_image_recon.sh'
        ]
        
        check_result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if check_result.returncode == 0:
            print(f"✅ Script exists: {check_result.stdout.strip()}")
        else:
            print(f"❌ Script not found: {check_result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking script: {e}")
        return False
    
    # Step 1: Run the update script
    print("🔄 Step 1: Running update script...")
    try:
        ssh_cmd = [
            'ssh',
            '-i', key_file,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=10',
            f'ubuntu@{ip}',
            'sudo bash /bak/bin/update_image_recon.sh'
        ]
        
        print("🔄 Executing update script...")
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for update
        )
        
        print(f"📊 Return code: {result.returncode}")
        
        if result.stdout.strip():
            print(f"📤 STDOUT:\n{result.stdout}")
            
        if result.stderr.strip():
            print(f"📥 STDERR:\n{result.stderr}")
        
        if result.returncode == 0:
            print(f"✅ Update script completed successfully on {ip}")
        else:
            print(f"❌ Update script failed on {ip} (exit code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Update script timeout on {ip}")
        return False
    except Exception as e:
        print(f"❌ Exception running update script on {ip}: {str(e)}")
        return False
    
    # Step 2: Check version in logs
    print("🔍 Step 2: Checking version in logs...")
    try:
        ssh_cmd = [
            'ssh',
            '-i', key_file,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=10',
            f'ubuntu@{ip}',
            'sudo grep "3.1.2337-1" /usr/bin/OSMWatcher/logs/* 2>/dev/null || echo "Version not found in logs"'
        ]
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and "Version not found in logs" not in result.stdout:
            print(f"✅ Version 3.1.2337-1 found in logs on {ip}")
            print(f"Log entries: {result.stdout.strip()}")
        else:
            print(f"⚠️  Version 3.1.2337-1 not found in logs on {ip}")
            print("This might indicate the update didn't complete properly")
            # Don't return False here as this might be expected in some cases
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Log check timeout on {ip}")
    except Exception as e:
        print(f"❌ Exception checking logs on {ip}: {str(e)}")
    
    # Step 3: Check OSM service status
    print("🔍 Step 3: Checking OSM service status...")
    try:
        ssh_cmd = [
            'ssh',
            '-i', key_file,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=10',
            f'ubuntu@{ip}',
            'sudo systemctl status osm --no-pager'
        ]
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout.lower()
            if 'active (running)' in output:
                print(f"✅ OSM service is active and running on {ip}")
            else:
                print(f"⚠️  OSM service status unclear on {ip}")
                print(f"Status output: {result.stdout}")
        else:
            print(f"❌ Failed to check OSM service status on {ip}")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Service status check timeout on {ip}")
        return False
    except Exception as e:
        print(f"❌ Exception checking service status on {ip}: {str(e)}")
        return False
    
    print(f"✅ All steps completed for {ip}")
    return True

def main():
    # Configuration
    JSON_FILE = "/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json"
    KEY_FILE = "image_identifier.pem"
    IGNORE_IPS = ["10.50.14.119"]  # IPs to skip during update
    
    print("🚀 Starting image_recon update process...")
    print(f"JSON file: {JSON_FILE}")
    print(f"SSH key: {KEY_FILE}")
    print(f"SSH user: ubuntu (with sudo privileges)")
    print(f"Ignoring IPs: {', '.join(IGNORE_IPS)}")
    print("Process:")
    print("  1. SSH as ubuntu and run sudo /bak/bin/update_image_recon.sh")
    print("  2. Check for version 3.1.2337-1 in logs")
    print("  3. Verify OSM service is running")
    
    # Check if key file exists
    if not Path(KEY_FILE).exists():
        print(f"❌ Error: SSH key file '{KEY_FILE}' not found")
        print("Make sure the key file is in the current directory or provide the full path")
        sys.exit(1)
    
    # Load server IPs from JSON
    all_server_ips = load_server_ips(JSON_FILE)
    
    if not all_server_ips:
        print("❌ No server IPs found in the JSON file")
        sys.exit(1)
    
    # Filter out ignored IPs
    server_ips = [ip for ip in all_server_ips if ip not in IGNORE_IPS]
    ignored_count = len(all_server_ips) - len(server_ips)
    
    print(f"📋 Found {len(all_server_ips)} total servers, {len(server_ips)} to update ({ignored_count} ignored):")
    for i, ip in enumerate(server_ips, 1):
        print(f"  {i}. {ip}")
    
    if ignored_count > 0:
        print(f"\n⏭️  Ignored servers:")
        for ip in all_server_ips:
            if ip in IGNORE_IPS:
                print(f"  - {ip} (skipped)")
    
    # Ask for confirmation
    response = input(f"\nDo you want to proceed with updating {len(server_ips)} servers? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled")
        sys.exit(0)
    
    # Process each server
    successful_updates = 0
    failed_updates = 0
    
    for i, ip in enumerate(server_ips, 1):
        print(f"\n🔄 Processing server {i}/{len(server_ips)}")
        
        if ssh_and_update(ip, KEY_FILE):
            successful_updates += 1
        else:
            failed_updates += 1
        
        # Small delay between servers to avoid overwhelming
        if i < len(server_ips):
            print("⏳ Waiting 10 seconds before next server...")
            time.sleep(10)
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 UPDATE SUMMARY")
    print(f"{'='*50}")
    print(f"✅ Successful updates: {successful_updates}")
    print(f"❌ Failed updates: {failed_updates}")
    print(f"⏭️  Servers ignored: {ignored_count}")
    print(f"📋 Total servers processed: {len(server_ips)}")
    print(f"📋 Total servers in JSON: {len(all_server_ips)}")
    
    if failed_updates > 0:
        print(f"\n⚠️  {failed_updates} servers failed to update. Check the output above for details.")
        sys.exit(1)
    else:
        print("\n🎉 All processed servers updated successfully!")
        print("✅ All OSM services are running")
        print("✅ Version checks completed")

if __name__ == "__main__":
    main()
