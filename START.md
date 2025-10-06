# 🚀 Start OSMTools v2.0

## Super Simple Startup

Just run this one command:

```bash
python3 run.py
```

That's it! The script will:
1. ✅ Install FastAPI if needed
2. ✅ Start the server automatically
3. ✅ Open on http://localhost:8000

## What You'll Get

- **🏠 Modern Dashboard**: Beautiful interface at http://localhost:8000
- **📊 Image Recon JSON**: Fully working tool (migrated from old JSON Generator)
- **📚 API Docs**: Automatic documentation at http://localhost:8000/docs
- **🔍 Health Check**: http://localhost:8000/health

## Clean Structure

```
OSMTools-master/
├── run.py                    # 🚀 Simple startup script
├── main.py                   # FastAPI application
├── config.py                 # Configuration
├── modules/                  # Clean modular structure
│   └── image_recon_json/     # Fully migrated tool
├── templates/                # Clean HTML templates
├── static/                   # Separated CSS & JS
└── requirements.txt          # Dependencies
```

## Next Steps

1. **Test the current setup** - Image Recon JSON is fully working!
2. **Migrate remaining tools** one by one:
   - Image Recon Service (Restart IR)
   - CCTV Tools
   - OSMachine (Machine Restart)
   - Config Editor (Box Editor)

## Stop the Server

Press `Ctrl+C` in the terminal.

---

**That's it! Clean, simple, and modern!** 🎉
