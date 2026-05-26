#!/usr/bin/env python3
"""Run the Watchfy backend server with HTTP/2 support."""
import os
import sys
import uvicorn
from uvicorn.config import Config

if __name__ == "__main__":
    # Set environment
    os.environ.setdefault("ENV", "development")
    
    config = Config(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("DEBUG", "false").lower() == "true",
        reload_dirs=["backend"],
        log_level="info",
        # Enable HTTP/2
        http="h2c",  # HTTP/2 with clear text (use "http/1.1" for HTTP/1 only)
        ws="auto",
        limit_max_requests=1000,
        timeout_keep_alive=30,
        # SSL context for HTTPS (optional)
        # ssl_keyfile=os.environ.get("SSL_KEYFILE"),
        # ssl_certfile=os.environ.get("SSL_CERTFILE"),
    )
    server = uvicorn.Server(config=config)
    server.run()