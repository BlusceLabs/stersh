"""Graceful shutdown endpoint for admin."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import sys
import time

from auth import get_current_active_user
from database import User

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/shutdown")
async def shutdown(
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Initiate graceful shutdown of the application."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Return immediate response while shutdown happens in background
    import threading
    def shutdown_app():
        # Give client time to receive response
        time.sleep(0.5)
        # Exit with code
        sys.exit(0)
    
    # Run shutdown in background thread so we can return response
    threading.Thread(target=shutdown_app, daemon=True).start()
    
    return JSONResponse(
        status_code=200,
        content={"message": "Server is shutting down..."},
        media_type="application/json"
    )