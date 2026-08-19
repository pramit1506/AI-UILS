from sqlalchemy import text
from loguru import logger
from app.database.session import async_engine, async_session_maker
from app.models import Base
from app.repositories.user_repository import user_repository
from app.core.security import get_password_hash


DEMO_USERS = [
  {
    "name": "Dr. Jane Smith",
    "role": "Quality Assurance Lead",
    "username": "dr_smith",
    "email": "jane.smith@pharma-qms.io",
    "password": "password123",
    "bio": "Lead Quality & Compliance Specialist with 10+ years QMS experience.",
  },
  {
    "name": "Alex Rivera",
    "role": "Compliance Officer",
    "username": "alex_rivera",
    "email": "alex.rivera@audit-corp.com",
    "password": "password123",
    "bio": "Regulatory Affairs & Pharmacovigilance Auditor.",
  },
  {
    "name": "Sarah Connor",
    "role": "Operations Director",
    "username": "sarah_c",
    "email": "sarah.c@manufacturing.org",
    "password": "password123",
    "bio": "Plant Operations & Batch Intake Director.",
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

        # Seed demo users
        await seed_demo_users()

        logger.info("Database initialized, migrated, and seeded successfully.")
    except Exception as exc:
        logger.warning(f"Database initialization encountered an error: {exc}")
