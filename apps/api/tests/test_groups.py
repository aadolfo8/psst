from datetime import date, timedelta

import pytest
from argon2 import PasswordHasher
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Participant
from app.security import SLUG_ALPHABET, session_cookie_name
from tests.conftest import create_group


async def test_create_group_makes_creator_admin_and_logs_in(client: AsyncClient) -> None:
    me = await create_group(client, exchange_date=str(date.today() + timedelta(days=30)))

    slug = me["group"]["slug"]
    assert len(slug) == 10
    assert set(slug) <= set(SLUG_ALPHABET)
    assert me["name"] == "Ana"
    assert me["is_admin"] is True
    assert me["group"]["status"] == "open"
    assert me["group"]["budget"] == 30
    assert session_cookie_name(slug) in client.cookies

    response = await client.get(f"/groups/{slug}/me")
    assert response.status_code == 200
    assert response.json() == me


async def test_budget_and_date_are_optional(client: AsyncClient) -> None:
    me = await create_group(client, budget=None)

    assert me["group"]["budget"] is None
    assert me["group"]["exchange_date"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "   "},
        {"admin_name": ""},
        {"pin": "123"},
        {"pin": "12a4"},
        {"pin": "١٢٣٤"},
        {"budget": 0},
        {"exchange_date": str(date.today() - timedelta(days=1))},
    ],
)
async def test_create_group_rejects_invalid_data(client: AsyncClient, overrides: dict) -> None:
    payload = {"name": "Familia", "admin_name": "Ana", "pin": "1234"} | overrides

    response = await client.post("/groups", json=payload)

    assert response.status_code == 422


async def test_get_group_returns_public_info(client: AsyncClient, new_client) -> None:
    me = await create_group(client)
    slug = me["group"]["slug"]

    async with new_client() as stranger:
        response = await stranger.get(f"/groups/{slug}")

    assert response.status_code == 200
    assert response.json() == {
        "slug": slug,
        "name": "Familia",
        "budget": 30,
        "exchange_date": None,
        "status": "open",
    }


async def test_get_unknown_group_is_404(client: AsyncClient) -> None:
    response = await client.get("/groups/noexiste00")

    assert response.status_code == 404


async def test_pin_is_stored_hashed(client: AsyncClient, db: AsyncSession) -> None:
    me = await create_group(client)

    pin_hash = await db.scalar(select(Participant.pin_hash).where(Participant.id == me["id"]))

    assert pin_hash is not None
    assert "1234" not in pin_hash
    assert PasswordHasher().verify(pin_hash, "1234")
