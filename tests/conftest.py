import asyncio
import os
from typing import AsyncGenerator, Generator
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ["ENV"] = "test"
os.environ["DEBUG"] = "False"
os.environ["SECRET_KEY"] = "test_secret_key_for_jwt_token_generation_32bytes"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)

from app.core.config import settings
from app.db.models import Base
from app.db.session import get_db
import app.db.session as db_session_module
import app.api.v1.endpoints.websocket as ws_endpoint_module
from app.main import app
from app.websocket.manager import manager

test_engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in settings.DATABASE_URL else None,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

db_session_module.AsyncSessionLocal = TestingSessionLocal
ws_endpoint_module.AsyncSessionLocal = TestingSessionLocal


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    manager._user_sockets.clear()
    manager._conversation_sockets.clear()
    manager._socket_metadata.clear()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def create_test_user(client: TestClient):
    def _create_user(username: str, email: str, password: str = "password123"):
        reg_res = client.post(
            "/api/v1/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        assert reg_res.status_code == 201, reg_res.text
        user_data = reg_res.json()

        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200, login_res.text
        token_data = login_res.json()

        return {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": email,
            "token": token_data["access_token"],
            "headers": {"Authorization": f"Bearer {token_data['access_token']}"},
        }

    return _create_user
