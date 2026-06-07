"""Version and build information."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/version", tags=["version"])

@router.get("/")
async def version_info() -> Dict[str, Any]:
    """Get version and build information."""
    commit = "unknown"
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        pass
    
    return {
        "version": "1.0.0",
        "git_commit": commit,
        "build_date": os.environ.get("BUILD_DATE", "unknown"),
        "built_by": os.environ.get("BUILD_BY", "unknown"),
        "python_version": os.environ.get("PYTHON_VERSION", "unknown"),
    }