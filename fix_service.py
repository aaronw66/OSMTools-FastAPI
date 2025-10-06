# Quick fix for get_image_recon_servers method

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

