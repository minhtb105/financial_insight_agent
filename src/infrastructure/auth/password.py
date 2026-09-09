"""Password hashing with bcrypt (direct, passlib-compatible hashes)."""

from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    # bcrypt truncates at 72 bytes; we handle explicitly
    pw_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False
