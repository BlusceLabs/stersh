"""Unit tests for backend/auth.py mass-assignment guard.

`update_user` is the privilege-escalation choke point. A caller who
forwards a request body containing `is_admin: true` or
`password_hash: '...'` MUST NOT be able to mutate those columns.
This test suite pins the exact allowlist and pins the failure mode.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

# auth.py imports from `database` at module load time, which requires
# SQLAlchemy + a real or mocked SessionLocal. We mock the User model
# and SessionLocal via sys.modules BEFORE importing auth.
import sys
import types

# Stub the database module to avoid pulling in real SQLAlchemy wiring.
fake_db = types.ModuleType("database")


class _FakeUser:
    is_active = True
    is_admin = False
    id = 1
    username = "alice"
    email = "a@example.com"
    password_hash = "x"


fake_db.User = _FakeUser
fake_db.Session = MagicMock()
fake_db.SessionLocal = MagicMock()  # backward compat for old imports


def _fake_get_db():
    yield MagicMock()


fake_db.get_db = _fake_get_db
sys.modules["database"] = fake_db

import auth  # noqa: E402


class UpdateUserFieldAllowlist(unittest.TestCase):
    def _db_with_user(self, **attrs):
        db = MagicMock()
        user = MagicMock(spec=_FakeUser)
        for k, v in attrs.items():
            setattr(user, k, v)
        db.query.return_value.filter.return_value.first.return_value = user
        return db, user

    def test_allows_email_change(self):
        db, user = self._db_with_user(email="old@example.com")
        auth.update_user(db, user_id=1, updates={"email": "new@example.com"})
        self.assertEqual(user.email, "new@example.com")
        db.commit.assert_called_once()

    def test_allows_username_change(self):
        db, user = self._db_with_user(username="old")
        auth.update_user(db, user_id=1, updates={"username": "new"})
        self.assertEqual(user.username, "new")

    def test_allows_both_email_and_username_together(self):
        db, user = self._db_with_user(email="o@x", username="o")
        auth.update_user(
            db, user_id=1, updates={"email": "n@x", "username": "n"}
        )
        self.assertEqual(user.email, "n@x")
        self.assertEqual(user.username, "n")

    def test_blocks_is_admin_mass_assignment(self):
        """THE critical guard: a request body that includes is_admin
        MUST NOT be persisted, and MUST raise 400."""
        db, user = self._db_with_user(is_admin=False)
        with self.assertRaises(HTTPException) as ctx:
            auth.update_user(
                db,
                user_id=1,
                updates={"is_admin": True, "username": "x"},
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("is_admin", ctx.exception.detail)
        # DB must not be committed on rejected update.
        db.commit.assert_not_called()

    def test_blocks_is_active_mass_assignment(self):
        db, user = self._db_with_user(is_active=True)
        with self.assertRaises(HTTPException) as ctx:
            auth.update_user(db, user_id=1, updates={"is_active": False})
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("is_active", ctx.exception.detail)
        db.commit.assert_not_called()

    def test_blocks_password_hash_mass_assignment(self):
        db, user = self._db_with_user(password_hash="$old")
        with self.assertRaises(HTTPException) as ctx:
            auth.update_user(
                db,
                user_id=1,
                updates={"password_hash": "$attacker-controlled"},
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("password_hash", ctx.exception.detail)
        db.commit.assert_not_called()

    def test_blocks_id_mass_assignment(self):
        """Cascade-rename attack: changing `id` to escalate to another user."""
        db, user = self._db_with_user(id=1)
        with self.assertRaises(HTTPException) as ctx:
            auth.update_user(db, user_id=1, updates={"id": 9999})
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("id", ctx.exception.detail)

    def test_blocks_unknown_field(self):
        db, user = self._db_with_user()
        with self.assertRaises(HTTPException) as ctx:
            auth.update_user(
                db, user_id=1, updates={"role": "superuser"}
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("role", ctx.exception.detail)

    def test_blocks_non_dict_updates(self):
        db, user = self._db_with_user()
        for bad in (None, "string", 42, ["a"], True):
            with self.assertRaises(HTTPException) as ctx:
                auth.update_user(db, user_id=1, updates=bad)
            self.assertEqual(ctx.exception.status_code, 400)

    def test_404_when_user_missing(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            auth.update_user(db, user_id=9999, updates={"email": "x@x"})
        self.assertEqual(ctx.exception.status_code, 404)


class AllowlistContents(unittest.TestCase):
    def test_allowlist_exact_contents(self):
        """The allowlist is small and intentional. Pin it so a
        careless refactor that adds a sensitive column triggers a
        test failure."""
        self.assertEqual(
            auth._UPDATABLE_USER_FIELDS,
            frozenset({"email", "username"}),
        )

    def test_allowlist_does_not_contain_sensitive_fields(self):
        sensitive = {
            "is_admin", "is_active", "is_superuser", "role",
            "password", "password_hash", "id", "created_at",
        }
        self.assertTrue(sensitive.isdisjoint(auth._UPDATABLE_USER_FIELDS))


if __name__ == "__main__":
    unittest.main()
