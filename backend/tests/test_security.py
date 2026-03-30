from __future__ import annotations

import sys
from pathlib import Path

import bcrypt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.security import PASSWORD_HASH_PREFIX, hash_password, verify_password


def test_hash_password_supports_long_ascii_password() -> None:
    password = "a" * 120

    hashed = hash_password(password)

    assert hashed.startswith(PASSWORD_HASH_PREFIX)
    assert verify_password(password, hashed) is True
    assert verify_password("b" * 120, hashed) is False


def test_hash_password_supports_long_unicode_password() -> None:
    password = "🙂परीक्षण密碼" * 20

    hashed = hash_password(password)

    assert hashed.startswith(PASSWORD_HASH_PREFIX)
    assert verify_password(password, hashed) is True


def test_verify_password_supports_legacy_bcrypt_hashes() -> None:
    password = "legacy-password-" + ("x" * 90)
    legacy_hash = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

    assert verify_password(password, legacy_hash) is True
    assert verify_password("wrong-password", legacy_hash) is False
