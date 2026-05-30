"""Package shim for watchfy.

Creates synthetic `services.streaming.app` entries in sys.modules that
point at the flat .py files in the project root — no subdirectory
restructuring needed.

Usage — import once at the top of main.py BEFORE any watchfy imports:
    import pkg_shim  # noqa: F401
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).parent

# ── Module map: dotted package path → flat filename ───────────────────────────
_MAP: dict[str, str] = {
    # Shared utilities
    "services.streaming.app.hls_parser":              "hls_parser",
    "services.streaming.app.subtitles":               "subtitles",
    "services.streaming.app.ffmpeg_utils":            "ffmpeg_utils",
    "services.streaming.app.ffmpeg_routes":           "ffmpeg_routes",
    "services.streaming.app.enhanced_proxy_routes":   "proxy_routes",
    # Black server (vidking.net)
    "services.streaming.app.black":                   "black",
    "services.streaming.app.black_routes":            "black_routes",
    # White server (111movies.net)
    "services.streaming.app.white":                   "white",
    "services.streaming.app.white_routes":            "white_routes",
    # Pink server (hydrahd.ru)
    "services.streaming.app.pink":                    "pink",
    "services.streaming.app.pink_routes":             "pink_routes",
}


def _ensure_pkg(dotted: str) -> None:
    """Create a stub package in sys.modules for every prefix of dotted."""
    parts = dotted.split(".")
    for i in range(1, len(parts) + 1):
        name = ".".join(parts[:i])
        if name not in sys.modules:
            pkg = types.ModuleType(name)
            pkg.__package__ = name
            pkg.__path__    = [str(_ROOT)]
            pkg.__spec__    = None
            sys.modules[name] = pkg


def _register_all() -> None:
    for pkg_path in ("services", "services.streaming", "services.streaming.app"):
        _ensure_pkg(pkg_path)

    for pkg_name, flat_name in _MAP.items():
        if pkg_name in sys.modules:
            continue
        path = _ROOT / f"{flat_name}.py"
        if not path.exists():
            # Non-fatal — some optional modules may not be present
            import logging
            logging.getLogger(__name__).warning(
                "pkg_shim: %s not found, skipping", path
            )
            continue
        spec = importlib.util.spec_from_file_location(pkg_name, path)
        if spec is None:
            raise ImportError(f"Cannot build spec for {path}")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name.rsplit(".", 1)[0]
        sys.modules[pkg_name] = mod
        if flat_name not in sys.modules:
            sys.modules[flat_name] = mod
        spec.loader.exec_module(mod)


_register_all()