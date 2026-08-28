from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import AsyncSessionLocal, engine


@pytest_asyncio.fixture(autouse=True)
async def dispose_engine_pool():
    """Disposes stale connections from SQLAlchemy pool after each test to prevent event loop mismatch."""
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
