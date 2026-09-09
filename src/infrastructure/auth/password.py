"""Password hashing with bcrypt (direct). Bcrypt limit is 72 bytes; longer passwords are pre-hashed with SHA-256 to avoid silent truncation collisions."""

from __future__ import annotations

import hashlib

import bcrypt


def _prepare_password(password: str) -> bytes:
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        # Pre-hash to 32 bytes (hex 64) to fit bcrypt limit, avoids truncation collision.
        # Using hex digest keeps deterministic and fits 72 bytes.
        pw_bytes = hashlib.sha256(pw_bytes).hexdigest().encode("utf-8")
    return pw_bytes


def hash_password(password: str) -> str:
    pw_bytes = _prepare_password(password)
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        # Try new pre-hashed path first
        if bcrypt.checkpw(_prepare_password(plain), hashed.encode("utf-8")):
            return True
        # Fallback for legacy truncated hashes (passwords created before pre-hash)
        legacy = plain.encode("utf-8")[:72]
        if legacy != _prepare_password(plain):
            return bcrypt.checkpw(legacy, hashed.encode("utf-8"))
        return False
    except Exception:
        return False
