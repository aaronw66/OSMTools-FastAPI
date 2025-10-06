# Image Recon Service Configuration

## How to Disable Development Mode

The Image Recon Service will automatically load **real server data** from a JSON configuration file. It checks these paths in order:

1. **Production Path** (on server): `/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json`
2. **Local Development Path**: `type/ir.json` (in this repo)

If neither file exists, it will show **mock/development servers** (the 3 servers with "DEV" badge you saw).

## How to Add Your Real Servers

### Option 1: Edit `type/ir.json` (for local testing)

Edit the file `type/ir.json` in this directory with your real server IPs:

```json
[
    {
        "targets": ["10.100.4.100:9100"],
        "labels": {
            "hostname": "IR-01-image-recon-server-01",
            "env": "production"
        }
    },
    {
        "targets": ["10.100.4.101:9100"],
        "labels": {
            "hostname": "IR-02-image-recon-server-02",
            "env": "production"
        }
    }
]
```

**Format Explanation:**
- `targets`: Array with IP:PORT (port is usually 9100, but only the IP part is used)
- `labels.hostname`: Server name (prefix before first `-` becomes the label, e.g., "IR-01" → shows as "IR-01")
- `labels.env`: Not used by the app, just for documentation

### Option 2: Use Production Config (on server)

On your production server at `/opt/compose-conf/tools/`, the app will automatically read from:
```
/opt/compose-conf/prometheus/config/conf.d/node/image-recon.json
```

This is the same format as above.

## Server Labels

The label shown in the UI is extracted from the hostname:
- `"IR-01-image-recon-server-01"` → Label: **IR-01**
- `"SRS-DC-server"` → Label: **SRS** (filtered out, won't show up)

## Testing

After editing `type/ir.json`:
1. Restart the server: `python3 run.py`
2. Check the console - you should see: `✅ Loaded X servers from type/ir.json`
3. Refresh the Image Recon Service page
4. Your real servers should appear instead of "Development Mode" mock servers

## Current Status

✅ Currently loading: **2 servers** from `type/ir.json`
- 10.100.4.100 (IR-01-image-recon-server-01)
- 10.100.4.101 (IR-02-image-recon-server-02)

