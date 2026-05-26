"""Shim — application moved to app.main."""
import os
from dotenv import load_dotenv
load_dotenv()

# Backward compat: old entry point (uvicorn main:app)
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app  # noqa: F401, E402
