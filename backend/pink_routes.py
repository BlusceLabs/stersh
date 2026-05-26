"""Shim — routes moved to app.api.providers.pink."""
from app.api.providers.pink import router, shutdown_pink_browser, shutdown_pink_client  # noqa: F401
