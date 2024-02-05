"""
Настройки подключения к БД
"""
import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


USER_ROOT = os.environ.get("MONGO_INITDB_ROOT_USERNAME", default="root")
USER_PASSWORD = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", default="example")

"""
Если проект запущен в docker, то возьмем настройки из env 
там название контейнера, в остальном локальная база
"""
if os.getenv('PYTEST_ENV') == 'docker':
    MONGO_HOST = os.environ.get("MONGO_HOST", default="localhost")
else:
    MONGO_HOST = "localhost"

MONGO_PORT = os.environ.get("MONGO_PORT", default="27017")
DEBUG = os.environ.get("DEBUG", default=False)

MONGODB_URL = (f"mongodb://{USER_ROOT}:{USER_PASSWORD}@"
               f"{MONGO_HOST}:{MONGO_PORT}?retryWrites=true&w=majority")


async def get_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(MONGODB_URL)
    if DEBUG:
        return client.test_databse
    return client["minesweeper"]
