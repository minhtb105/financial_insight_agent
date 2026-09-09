"""Seed admin user from env — idempotent."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from infrastructure.auth.password import hash_password
from infrastructure.db.base import get_session_factory
from infrastructure.db.models.user import User

logger = logging.getLogger(__name__)


async def seed_admin() -> None:
    """Create admin user if not exists, update password if ADMIN_PASSWORD changed (optional)."""
    import os

    admin_email = os.getenv("ADMIN_EMAIL", "admin@finsight.vn").lower().strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_name = os.getenv("ADMIN_NAME", "Admin")

    if not admin_email or not admin_password:
        logger.warning("ADMIN_EMAIL/PASSWORD not set — skipping admin seed")
        return

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(User).where(User.email == admin_email))
        existing = result.scalar_one_or_none()
        if existing is not None:
            # Ensure role is admin
            if existing.role != "admin":
                existing.role = "admin"
                await session.commit()
                logger.info("Promoted existing user %s to admin", admin_email)
            else:
                logger.info("Admin user %s already exists", admin_email)
            return

        now = datetime.now(timezone.utc)
        user = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            name=admin_name,
            role="admin",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        await session.commit()
        logger.info("Seeded admin user %s", admin_email)


async def seed_demo_user() -> None:
    """Optional demo user for convenience."""
    import os

    demo_email = os.getenv("DEMO_EMAIL", "demo@finsight.vn").lower().strip()
    demo_password = os.getenv("DEMO_PASSWORD", "demo123")
    if not demo_email:
        return
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(User).where(User.email == demo_email))
        if result.scalar_one_or_none() is not None:
            return
        now = datetime.now(timezone.utc)
        user = User(
            email=demo_email,
            hashed_password=hash_password(demo_password),
            name="Nhà đầu tư Demo",
            role="user",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        await session.commit()
        logger.info("Seeded demo user %s", demo_email)
