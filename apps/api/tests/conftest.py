from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import push
from app.config import get_settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import Assignment

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
        # Las demás tablas cuelgan de estas y se vacían en cascada.
        await conn.execute(text("TRUNCATE groups CASCADE"))


@pytest.fixture
def sent(monkeypatch) -> list[dict[str, Any]]:
    """Activa las push con claves falsas y captura cada envío: (endpoint, payload)."""
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_private_key", "privada")
    monkeypatch.setattr(settings, "vapid_public_key", "publica")

    calls: list[dict[str, Any]] = []

    def fake_webpush(subscription_info, data, **kwargs):
        calls.append({"endpoint": subscription_info["endpoint"], "data": data})

    monkeypatch.setattr(push, "webpush", fake_webpush)
    return calls


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


NAMES = ["Luis", "Marta", "Pablo"]


@pytest.fixture
async def drawn(client: AsyncClient, new_client, db: AsyncSession) -> Any:
    """Grupo de cuatro ya sorteado. `pairs` dice quién regala a quién (leído de la BD, sin
    revelar nada por la API) para que los tests sepan qué cliente es cada lado."""
    ana = await create_group(client)
    slug = ana["group"]["slug"]
    async with (
        new_client() as luis_client,
        new_client() as marta_client,
        new_client() as pablo_client,
    ):
        clients = {"Ana": client, "Luis": luis_client, "Marta": marta_client, "Pablo": pablo_client}
        ids = {"Ana": ana["id"]}
        for name in NAMES:
            ids[name] = (await join(clients[name], slug, name))["id"]
        await client.patch(f"/groups/{slug}", json={"status": "closed"})
        assert (await client.post(f"/groups/{slug}/draw")).status_code == 200

        names = {id_: name for name, id_ in ids.items()}
        rows = (await db.execute(select(Assignment.giver_id, Assignment.receiver_id))).all()
        pairs = {names[str(giver)]: names[str(receiver)] for giver, receiver in rows}
        yield {"slug": slug, "clients": clients, "ids": ids, "pairs": pairs}


def a_pair(drawn) -> tuple[str, str]:
    """Nombres de una pareja cualquiera: (quien regala, quien recibe)."""
    return next(iter(drawn["pairs"].items()))
