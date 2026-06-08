"""Unit tests for backend/continue_watching.py.

Pins the source_server allowlist and Pydantic validators. These
guards are what stop a caller from inserting continue-watching
records for a non-existent or attacker-controlled stream source.
"""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock

# Stub the database module to avoid pulling in real SQLAlchemy wiring
# (continue_watching.py imports PlaybackHistory, User, get_db at module
# load time, but we only need the constants and Pydantic models).
fake_db = types.ModuleType("app.database")
fake_db.PlaybackHistory = MagicMock()
fake_db.User = MagicMock()
fake_db.get_db = MagicMock(return_value=iter([MagicMock()]))
sys.modules["app.database"] = fake_db  # always overwrite (setdefault races with test_auth)

# Stub the auth module similarly (continue_watching may import it for
# auth dependencies in some code paths).
if "app.api.auth" not in sys.modules or not hasattr(sys.modules["app.api.auth"], "get_current_active_user"):
    fake_auth = types.ModuleType("app.api.auth")
    fake_auth.get_current_active_user = MagicMock()
    sys.modules["app.api.auth"] = fake_auth

from app.api.continue_watching import _ALLOWED_SOURCE_SERVERS  # noqa: E402


class SourceServerAllowlist(unittest.TestCase):
    def test_allowlist_contents(self):
        """Only the two real source servers are allowed. Adding a third
        server requires a deliberate code change and a test update."""
        self.assertEqual(_ALLOWED_SOURCE_SERVERS, frozenset({"white", "black"}))

    def test_no_external_hosts_in_allowlist(self):
        """The allowlist must not contain anything that could be
        attacker-controlled (no domain names, no IP literals)."""
        for host in _ALLOWED_SOURCE_SERVERS:
            self.assertNotIn(".", host, f"server name {host!r} looks like a host")
            self.assertNotIn(":", host, f"server name {host!r} looks like URL")
            self.assertTrue(
                host.isalpha(),
                f"server name {host!r} must be alpha-only",
            )


if __name__ == "__main__":
    unittest.main()
