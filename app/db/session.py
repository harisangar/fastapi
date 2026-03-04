from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import get_settings

settings = get_settings()
from sqlalchemy import text



# ============================
# Engine Configuration
# ============================

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,       # Detect stale connections
    pool_size=10,             # Default pool size
    max_overflow=20,          # Extra burst connections
)

# ============================
# Session Factory
# ============================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================
# Dependency (FastAPI)
# ============================



async def test_db_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connected successfully!")
    except Exception as e:
        print("❌ Database connection failed!")
        print(e)
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a DB session.
    Ensures proper cleanup after request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()