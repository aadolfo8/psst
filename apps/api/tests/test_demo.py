"""Modo demo: grupo de ejemplo y cambio de persona sin PIN."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group
from tests.conftest import create_group


async def test_demo_enters_as_lucia_in_a_drawn_group(client: AsyncClient) -> None:
    response = await client.post("/demo")

    assert response.status_code == 201
    me = response.json()
    assert me["name"] == "Lucía"
    assert me["revealed"] is True
    assert me["group"]["status"] == "drawn"
    assert me["group"]["demo"] is True
    slug = me["group"]["slug"]
    assert (await client.post(f"/groups/{slug}/me/reveal")).json()["receiver"]["name"] == "Mario"
    messages = (await client.get(f"/groups/{slug}/chat/giver")).json()["messages"]
    assert len(messages) == 4


async def test_switch_shows_the_other_side_anonymously(client: AsyncClient) -> None:
    slug = (await client.post("/demo")).json()["group"]["slug"]

    response = await client.post(f"/groups/{slug}/demo/switch", json={"name": "mario"})

    assert response.status_code == 200
    assert response.json()["name"] == "Mario"
    as_receiver = await client.get(f"/groups/{slug}/chat/receiver")
    assert len(as_receiver.json()["messages"]) == 4
    assert "Lucía" not in as_receiver.text


async def test_switch_only_works_in_demo_groups(client: AsyncClient, new_client) -> None:
    slug = (await create_group(client))["group"]["slug"]

    async with new_client() as stranger:
        response = await stranger.post(f"/groups/{slug}/demo/switch", json={"name": "Ana"})
        still_out = await stranger.get(f"/groups/{slug}/me")

    assert response.status_code == 404
    assert still_out.status_code == 401


async def test_each_visit_gets_its_own_demo_group(client: AsyncClient, new_client) -> None:
    first = (await client.post("/demo")).json()["group"]["slug"]
    async with new_client() as other:
        second = (await other.post("/demo")).json()["group"]["slug"]

    assert first != second


async def test_old_demo_groups_are_removed(client: AsyncClient, db: AsyncSession) -> None:
    await client.post("/demo")
    await db.execute(
        update(Group)
        .where(Group.demo.is_(True))
        .values(created_at=datetime.now(UTC) - timedelta(days=2))
    )
    await db.commit()

    await client.post("/demo")

    demo_groups = await db.scalar(select(func.count()).select_from(Group).where(Group.demo))
    assert demo_groups == 1


async def test_demo_has_guesses_and_lucia_can_unmask(client: AsyncClient) -> None:
    """Tres apuestas ya hechas (falta la de Lucía) y Lucía, que organiza, puede quitar las
    celosías para ver el final."""
    slug = (await client.post("/demo")).json()["group"]["slug"]

    status = (await client.get(f"/groups/{slug}/guess")).json()
    unmasked = await client.post(f"/groups/{slug}/unmask", json={"confirm": "desenmascarar"})
    results = (await client.get(f"/groups/{slug}/results")).json()["pairs"]

    assert status == {"guessed": None, "guessers": 3, "participants": 4}
    assert unmasked.status_code == 200
    assert [p["giver"]["name"] for p in results] == ["Lucía", "Mario", "Carmen", "Pablo"]
    assert [p["receiver"]["name"] for p in results if p["guessed_right"]] == ["Mario"]
