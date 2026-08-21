from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker , create_async_engine
from app.config.settings import get_settings
from app.observability.models import Base

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
    """Create tables if they don't exist. Fine for V1 — we'll move to
    Alembic migrations once the schema needs to evolve carefully."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> AsyncSession:
    return async_session_maker()