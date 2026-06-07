"""System information endpoint."""
from __future__ import annotations

import os
import platform
import time
from typing import Any, Dict

from fastapi import APIRouter

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
        "pid": os.getpid(),
        "current_dir": os.getcwd(),
    }
