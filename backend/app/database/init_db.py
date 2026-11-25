from sqlalchemy import text
from loguru import logger
from app.database.session import async_engine, async_session_maker
from app.database.search_v1 import install_search_v1
from app.database.workspace_v2 import install_workspace_v2
from app.database.identifier_prefixes import install_identifier_prefixes
from app.models import Base
from app.repositories.user_repository import user_repository
from app.core.security import get_password_hash
from app.core.config import settings


DEMO_USERS = [
  {
    "name": "Dr. Jane Smith",
    "role": "Quality Assurance Lead",
    "username": "dr_smith",
    "email": "jane.smith@example.com",
    "password": "password123",
    "bio": "Sample account for guided product tours.",
  },
  {
    "name": "Alex Rivera",
    "role": "Compliance Officer",
    "username": "alex_rivera",
    "email": "alex.rivera@example.com",
    "password": "password123",
    "bio": "Sample account showing role-based profile fields.",
  },
  {
    "name": "Sarah Connor",
    "role": "Operations Director",
    "username": "sarah_c",
    "email": "sarah.c@example.com",
    "password": "password123",
    "bio": "Sample account for multi-user tour scenarios.",
  },
]


async def seed_demo_users():
    """Seed initial demo accounts if not present."""
    async with async_session_maker() as session:
        for demo in DEMO_USERS:
            existing = await user_repository.get_by_username(session, demo["username"])
            if not existing:
                await user_repository.create_user(
                    session,
                    email=demo["email"],
                    username=demo["username"],
                    full_name=demo["name"],
                    hashed_password=get_password_hash(demo["password"]),
                    role=demo["role"],
                    bio=demo["bio"],
                )
                logger.info(f"Seeded demo account: @{demo['username']}")


async def init_database():
    """
    Ensure all database tables, required schema columns, and default demo accounts exist.
    Called on FastAPI application startup.
    """
    try:
        async with async_engine.begin() as conn:
            # Create any missing tables (users, log_record, etc.)
            await conn.run_sync(Base.metadata.create_all)
            
            # Check if user_id column is missing from log_record table
            try:
                result = await conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'log_record' AND column_name = 'user_id'"
                    )
                )
                if not result.scalar_one_or_none():
                    logger.info("Migrating log_record table: adding user_id column...")
                    await conn.execute(
                        text(
                            "ALTER TABLE log_record "
                            "ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL"
                        )
                    )
                    await conn.execute(
                        text("CREATE INDEX IF NOT EXISTS ix_log_record_user_id ON log_record (user_id)")
                    )
                    logger.info("Successfully added user_id column to log_record table.")
            except Exception as migration_exc:
                logger.debug(f"Schema column check skipped or not applicable: {migration_exc}")

            # Existing installations may have been bootstrapped without Alembic.
            search_ready = await conn.scalar(text(
                "SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'log_record'::regclass "
                "AND attname = 'search_terms' AND NOT attisdropped)"
            ))
            if not search_ready:
                await conn.run_sync(install_search_v1)
            if not await conn.scalar(text("SELECT to_regclass('ix_log_record_search_prefixes') IS NOT NULL")):
                await conn.run_sync(install_workspace_v2, legacy_index=False)
                await conn.run_sync(install_identifier_prefixes)

        # Seed demo users only in DEBUG mode — the accounts use a publicly
        # known password in source code, so they must never exist in any
        # deployed environment.
        if settings.DEBUG:
            await seed_demo_users()
            logger.info("Database initialized, migrated, and seeded successfully (DEBUG mode: demo users enabled).")
        else:
            logger.info("Database initialized and migrated successfully (demo seeding skipped: DEBUG=False).")
    except Exception as exc:
        # Surface DB problems loudly instead of starting "successfully" in a
        # broken state (readiness probes used to pass while every request 500'd).
        logger.error(f"Database initialization FAILED: {exc}")
