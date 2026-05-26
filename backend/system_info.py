"""System information endpoint."""
from fastapi import APIRouter, Depends
import platform
import os
import getpass
import uuid

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/info")
async def system_info() -> Dict[str, Any]:
    """Get system information."""
    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "user": getpass.getuser(),
        "current_dir": os.getcwd(),
        "pid": os.getpid(),
        "uptime": time.time() - platform.start_time(),
        "environment": dict(os.environ)
    }