from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from .service import OSMachineService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
service = OSMachineService()

@router.get("/")
async def show_osmachine_page(request: Request):
    """Show OSMachine page"""
    try:
        # Read machines from lognavigator.xml
        machines = service.read_machines_from_lognavigator(force_remote=False)
        
        # Get filtering info
        filter_info = service.get_allowed_groups_info()
        
        if not machines:
            service.logger.warning("⚠️ No machines found in allowed groups from lognavigator.xml")
            return templates.TemplateResponse('osmachine.html', {
                "request": request,
                "machine_groups": {},
                "categorized_machines": {},
                "filter_info": filter_info
            })
        
        # Organize machines by category
        categorized_machines = service.organize_machines_by_category(machines)
        
        total_machines = sum(len(machines[group]) for group in machines)
        total_categories = len(categorized_machines)
        
        service.logger.info(f"📊 Loaded {total_machines} machines from {len(machines)} allowed groups organized into {total_categories} categories")
        
        return templates.TemplateResponse('osmachine.html', {
            "request": request,
            "machine_groups": machines,
            "categorized_machines": categorized_machines,
            "filter_info": filter_info
        })
        
    except Exception as e:
        service.logger.error(f"❌ Error loading OSMachine page: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/check-machine-status")
async def check_machine_status(request: Request):
    """Check status of a single machine"""
    try:
        data = await request.json()
        machine_ip = data.get('machine_ip')
        
        if not machine_ip:
            return JSONResponse(content={"status": "error", "message": "Machine IP is required"}, status_code=400)
        
        is_online, status_message = service.check_machine_status(machine_ip)
        
        return JSONResponse(content={
            "status": "success",
            "is_online": is_online,
            "status_message": status_message,
            "machine_ip": machine_ip
        })
        
    except Exception as e:
        service.logger.error(f"❌ Error checking status: {str(e)}")
        return JSONResponse(content={
            "status": "error", 
            "message": str(e),
            "is_online": False,
            "status_message": "Error checking status"
        }, status_code=500)

@router.post("/restart-machine")
async def restart_machine(request: Request):
    """Restart a single machine"""
    try:
        data = await request.json()
        machine_ip = data.get('machine_ip')
        operation_mode = data.get('operation_mode', 'soft_restart')
        
        if not machine_ip:
            return JSONResponse(content={"status": "error", "message": "Machine IP is required"}, status_code=400)
        
        if operation_mode not in service.get_operation_modes():
            return JSONResponse(content={"status": "error", "message": f"Invalid operation mode: {operation_mode}"}, status_code=400)
        
        success, message = service.restart_machine(machine_ip, operation_mode)
        
        if success:
            mode_info = service.get_operation_modes()[operation_mode]
            return JSONResponse(content={
                "status": "success",
                "message": f"{mode_info['name']} initiated for machine {machine_ip}: {message}",
                "operation_mode": operation_mode,
                "mode_info": mode_info
            })
        else:
            return JSONResponse(content={
                "status": "error",
                "message": f"Failed to restart machine {machine_ip}: {message}",
                "operation_mode": operation_mode
            }, status_code=500)
            
    except Exception as e:
        service.logger.error(f"❌ Error in restart_machine: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.post("/batch-check-status")
async def batch_check_status(request: Request):
    """Check status of multiple machines concurrently with caching"""
    try:
        data = await request.json()
        machines_to_check = data.get('machines', [])
        max_concurrent = data.get('max_concurrent', 20)
        force_refresh = data.get('force_refresh', False)
        
        if not machines_to_check:
            return JSONResponse(content={
                "status": "error",
                "message": "No machines provided"
            }, status_code=400)
        
        results = service.batch_check_status(machines_to_check, max_concurrent, use_cache=not force_refresh)
        
        # Calculate health summary
        online_count = sum(1 for r in results.values() if r['status'] == 'online')
        offline_count = sum(1 for r in results.values() if r['status'] == 'offline')
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        
        health_summary = {
            'total': len(results),
            'online': online_count,
            'offline': offline_count,
            'error': error_count,
            'health_percentage': round((online_count / len(results) * 100), 2) if results else 0
        }
        
        return JSONResponse(content={
            "status": "success",
            "group_name": group_name,
            "results": results,
            "health_summary": health_summary,
            "timestamp": results[list(results.keys())[0]]['timestamp'] if results else None
        })
        
    except Exception as e:
        service.logger.error(f"❌ Error in batch_check_status: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.post("/check-all-machines")
async def check_all_machines(request: Request):
    """Check status of ALL machines with optimized performance and caching"""
    try:
        data = await request.json() if request.headers.get('content-type') == 'application/json' else {}
        force_refresh = data.get('force_refresh', False)
        
        machines = service.read_machines_from_lognavigator()
        
        if not machines:
            return JSONResponse(content={
                "status": "error",
                "message": "No machines found"
            }, status_code=404)
        
        # Flatten all machines into a single list
        all_machines = []
        for group_name, group_machines in machines.items():
            for machine in group_machines:
                machine['group_name'] = group_name
                all_machines.append(machine)
        
        service.logger.info(f"🚀 Starting bulk status check for {len(all_machines)} machines (force_refresh={force_refresh})...")
        
        # Use high concurrency for bulk operations with caching
        results = service.batch_check_status(all_machines, max_concurrent=30, use_cache=not force_refresh)
        
        # Calculate overall health
        online_count = sum(1 for r in results.values() if r['status'] == 'online')
        offline_count = sum(1 for r in results.values() if r['status'] == 'offline')
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        
        # Calculate per-group statistics
        group_stats = {}
        for group_name in machines.keys():
            group_machines = [r for r in results.values() if r['display_group'] == group_name]
            group_online = sum(1 for m in group_machines if m['status'] == 'online')
            group_offline = sum(1 for m in group_machines if m['status'] == 'offline')
            group_error = sum(1 for m in group_machines if m['status'] == 'error')
            group_total = len(group_machines)
            group_stats[group_name] = {
                'total': group_total,
                'online': group_online,
                'offline': group_offline,
                'error': group_error
            }
        
        service.logger.info(f"✅ Bulk status check complete: {online_count} online, {offline_count} offline, {error_count} errors")
        
        return JSONResponse(content={
            "status": "success",
            "total_machines": len(all_machines),
            "online_count": online_count,
            "offline_count": offline_count,
            "error_count": error_count,
            "group_stats": group_stats,
            "results": results,
            "timestamp": list(results.values())[0]['timestamp'] if results else None
        })
        
    except Exception as e:
        service.logger.error(f"❌ Error in check_all_machines: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.post("/get-machine-logs")
async def get_machine_logs(request: Request):
    """Get logs from a machine"""
    try:
        data = await request.json()
        machine_ip = data.get('machine_ip')
        date = data.get('date')
        lines = data.get('lines', 100)
        
        if not machine_ip:
            return JSONResponse(content={"status": "error", "message": "Machine IP is required"}, status_code=400)
        
        result = service.get_machine_logs(machine_ip, date, lines)
        
        if result['status'] == 'error':
            return JSONResponse(content=result, status_code=500)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        service.logger.error(f"❌ Error in get_machine_logs: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.post("/refresh-machines")
async def refresh_machines(request: Request):
    """Refresh machine list and clear cache"""
    try:
        # Clear cache when refreshing
        service.clear_status_cache()
        
        result = service.refresh_machines()
        
        if result['status'] == 'error':
            return JSONResponse(content=result, status_code=500)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        service.logger.error(f"❌ Error refreshing machine list: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.post("/clear-cache")
async def clear_cache(request: Request):
    """Clear machine status cache"""
    try:
        service.clear_status_cache()
        return JSONResponse(content={
            "status": "success",
            "message": "Machine status cache cleared successfully"
        })
    except Exception as e:
        service.logger.error(f"❌ Error clearing cache: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.get("/get-operation-modes")
async def get_operation_modes():
    """Get available operation modes"""
    try:
        return JSONResponse(content={
            "status": "success",
            "operation_modes": service.get_operation_modes()
        })
    except Exception as e:
        service.logger.error(f"❌ Error in get_operation_modes: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)

@router.post("/batch-restart")
async def batch_restart(request: Request):
    """Restart multiple machines in a group"""
    try:
        data = await request.json()
        group_name = data.get('group_name')
        operation_mode = data.get('operation_mode', 'soft_restart')
        max_concurrent = data.get('max_concurrent', 3)
        
        if operation_mode not in service.get_operation_modes():
            return JSONResponse(content={
                "status": "error",
                "message": f"Invalid operation mode: {operation_mode}"
            }, status_code=400)
        
        machines = service.read_machines_from_lognavigator()
        
        if not machines or group_name not in machines:
            return JSONResponse(content={
                "status": "error",
                "message": f"Group '{group_name}' not found"
            }, status_code=404)
        
        group_machines = machines[group_name]
        results = {}
        
        # Use ThreadPoolExecutor for concurrent restarts
        from concurrent import futures
        from threading import Lock
        from datetime import datetime
        
        lock = Lock()
        
        def restart_single_machine(machine):
            ip = machine['ip']
            try:
                success, message = service.restart_machine(ip, operation_mode)
                with lock:
                    results[ip] = {
                        'ip': ip,
                        'config_id': machine['config_id'],
                        'operation_mode': operation_mode,
                        'success': success,
                        'message': message,
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                with lock:
                    results[ip] = {
                        'ip': ip,
                        'config_id': machine['config_id'],
                        'operation_mode': operation_mode,
                        'success': False,
                        'message': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
        
        with futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_list = [executor.submit(restart_single_machine, machine) for machine in group_machines]
            futures.wait(future_list)
        
        # Calculate summary
        successful = len([r for r in results.values() if r['success']])
        failed = len([r for r in results.values() if not r['success']])
        
        return JSONResponse(content={
            "status": "success",
            "group_name": group_name,
            "operation_mode": operation_mode,
            "results": results,
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "success_rate": round((successful / len(results) * 100), 2) if results else 0
            },
            "timestamp": list(results.values())[0]['timestamp'] if results else None
        })
        
    except Exception as e:
        service.logger.error(f"❌ Error in batch_restart: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": str(e)
        }, status_code=500)