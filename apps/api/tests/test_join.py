import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, ParticipantSession
from app.security import hash_token, session_cookie_name
from tests.conftest import create_group, join


async def test_join_creates_participant_and_logs_in(client: AsyncClient, new_client) -> None:
    slug = (await create_group(client))["group"]["slug"]

    async with new_client() as luis:
        me = await join(luis, slug, "  Luis   García ")
        response = await luis.get(f"/groups/{slug}/me")

    assert me["name"] == "Luis García"
    assert me["is_admin"] is False
    assert response.status_code == 200
    assert response.json() == me


@pytest.mark.parametrize("name", ["Ana", "ana", "  ANA  "])
async def test_join_with_taken_name_is_409(client: AsyncClient, new_client, name: str) -> None:
    slug = (await create_group(client))["group"]["slug"]

    async with new_client() as other:
        response = await other.post(
            f"/groups/{slug}/participants", json={"name": name, "pin": "0000"}
        )

    assert response.status_code == 409
    assert "PIN" in response.json()["detail"]


@pytest.mark.parametrize("group_status", ["closed", "drawn"])
async def test_cannot_join_when_group_is_not_open(
    client: AsyncClient, new_client, db: AsyncSession, group_status: str
) -> None:
    slug = (await create_group(client))["group"]["slug"]
    await db.execute(update(Group).where(Group.slug == slug).values(status=group_status))
    await db.commit()

    async with new_client() as late:
        response = await late.post(
            f"/groups/{slug}/participants", json={"name": "Luis", "pin": "5678"}
        )

    assert response.status_code == 409


async def test_join_unknown_group_is_404(client: AsyncClient) -> None:
    response = await client.post(
        "/groups/noexiste00/participants", json={"name": "Luis", "pin": "5678"}
    )

    assert response.status_code == 404


async def test_session_token_is_stored_hashed(client: AsyncClient, db: AsyncSession) -> None:
    me = await create_group(client)
    token = client.cookies[session_cookie_name(me["group"]["slug"])]

    stored = (await db.scalars(select(ParticipantSession.token_hash))).all()

    assert stored == [hash_token(token)]
    assert token not in stored
