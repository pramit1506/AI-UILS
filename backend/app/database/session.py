from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.database.url import async_database_connection

db_url, connect_args = async_database_connection(settings.DATABASE_URL)

async_engine = create_async_engine(
    db_url,
    connect_args=connect_args,
    echo=settings.DEBUG,
    hide_parameters=True,
    pool_pre_ping=True,
    future=True,
)

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)
