import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

Base = declarative_base()
engine = create_async_engine(url=settings.database.url(), echo=False, future=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)


async def get_session():
    """
    Provide a transactional database session.

    :return: database session generator
    """

    session: AsyncSession = SessionLocal()
    try:
        yield session
    finally:
        await session.close()


async def init_models() -> None:
    """
    Initialize database schema.

    :return: None
    """

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def sync_init_models() -> None:
    """
    Run async model initialization in a synchronous context.

    :return: None
    """

    asyncio.run(init_models())
