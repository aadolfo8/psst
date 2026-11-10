from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine
from app.main import app

ClientFactory = Callable[[], AbstractAsyncContextManager[AsyncClient]]


@asynccontextmanager
async def _new_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with _new_client() as c:
        yield c


@pytest.fixture
def new_client() -> ClientFactory:
    """Un cliente sin cookies: simula otra persona u otro dispositivo."""
    return _new_client


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    """Sesión de BD para comprobar o preparar datos directamente en los tests."""
    async with SessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    yield
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE groups, participants, sessions CASCADE"))


async def create_group(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    """Crea un grupo con Ana como organizadora (PIN 1234) y devuelve la respuesta (`Me`)."""
    payload = {"name": "Familia", "budget": 30, "admin_name": "Ana", "pin": "1234"} | overrides
    response = await client.post("/groups", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def join(client: AsyncClient, slug: str, name: str, pin: str = "5678") -> dict[str, Any]:
    response = await client.post(f"/groups/{slug}/participants", json={"name": name, "pin": pin})
    assert response.status_code == 201, response.text
    return response.json()
