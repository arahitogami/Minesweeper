"""
Этот модуль содержит тестового клиента и подключение к тестовой базе данных
для тестов
"""

from typing import AsyncGenerator

import pytest

from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from main import app


@pytest.fixture(scope="session")
async def ac() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
async def db() -> AsyncIOMotorDatabase:
    return await get_db()
