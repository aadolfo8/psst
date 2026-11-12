import asyncio
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assignment
from tests.conftest import create_group, join
from tests.test_push import subscribe

NAMES = ["Luis", "Marta", "Pablo"]


@pytest.fixture
async def group(client: AsyncClient, new_client) -> Any:
    """Ana (organizadora) más Luis, Marta y Pablo, cada uno con su cliente."""
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
        yield {"slug": slug, "clients": clients, "ids": ids, "admin": client}


async def close(group) -> None:
    response = await group["admin"].patch(f"/groups/{group['slug']}", json={"status": "closed"})
    assert response.status_code == 200


async def draw(group):
    return await group["admin"].post(f"/groups/{group['slug']}/draw")


async def reveal(client: AsyncClient, slug: str):
    return await client.post(f"/groups/{slug}/me/reveal")


async def count_assignments(db: AsyncSession) -> int:
    return await db.scalar(select(func.count()).select_from(Assignment))


# --- quién puede sortear y cuándo ----------------------------------------------------------


async def test_only_admin_can_draw(group) -> None:
    await close(group)

    response = await group["clients"]["Luis"].post(f"/groups/{group['slug']}/draw")

    assert response.status_code == 403


async def test_cannot_draw_while_registrations_are_open(group) -> None:
    response = await draw(group)

    assert response.status_code == 409
    assert "cierra" in response.json()["detail"]


async def test_needs_at_least_three_people(client: AsyncClient, new_client) -> None:
    slug = (await create_group(client))["group"]["slug"]
    async with new_client() as luis:
        await join(luis, slug, "Luis")
    await client.patch(f"/groups/{slug}", json={"status": "closed"})

    response = await client.post(f"/groups/{slug}/draw")

    assert response.status_code == 422
    assert "3 personas" in response.json()["detail"]


# --- el sorteo -----------------------------------------------------------------------------


async def test_draw_saves_assignments_without_revealing_them(group, db: AsyncSession) -> None:
    await close(group)

    response = await draw(group)

    assert response.status_code == 200
    # La respuesta es solo la info pública del grupo: el organizador no ve a quién toca nadie.
    assert set(response.json()) == {
        "slug",
        "name",
        "budget",
        "exchange_date",
        "status",
        "demo",
        "unmasked_at",
    }
    assert response.json()["status"] == "drawn"
    assert await count_assignments(db) == 4


async def test_impossible_draw_explains_why_and_changes_nothing(group, db: AsyncSession) -> None:
    admin, slug, ids = group["admin"], group["slug"], group["ids"]
    for other in NAMES:
        await admin.post(
            f"/groups/{slug}/exclusions",
            json={"participant_a_id": ids["Ana"], "participant_b_id": ids[other]},
        )
    await close(group)

    response = await draw(group)

    assert response.status_code == 422
    assert response.json()["detail"] == "Ana no puede regalar a nadie con estas exclusiones"
    assert (await admin.get(f"/groups/{slug}")).json()["status"] == "closed"
    assert await count_assignments(db) == 0


async def test_parallel_draws_leave_a_single_valid_draw(group, db: AsyncSession) -> None:
    await close(group)

    responses = await asyncio.gather(draw(group), draw(group))

    assert all(r.status_code == 200 for r in responses)
    rows = (await db.execute(select(Assignment.giver_id, Assignment.receiver_id))).all()
    assert len(rows) == 4
    assert len({giver for giver, _ in rows}) == len({receiver for _, receiver in rows}) == 4


# --- revelado ------------------------------------------------------------------------------


async def test_each_person_reveals_someone_else_with_their_wishlist(group) -> None:
    slug, clients = group["slug"], group["clients"]
    await clients["Marta"].put(f"/groups/{slug}/me/wishlist", json={"wishlist": "plantas"})
    await close(group)
    await draw(group)

    receivers = {}
    for name, client in clients.items():
        response = await reveal(client, slug)
        assert response.status_code == 200
        receiver = response.json()["receiver"]
        assert receiver["name"] != name
        receivers[name] = receiver

    assert sorted(r["name"] for r in receivers.values()) == sorted(clients)
    marta = next(r for r in receivers.values() if r["name"] == "Marta")
    assert marta["wishlist"] == "plantas"


async def test_reveal_is_repeatable_and_marks_as_seen(group) -> None:
    slug, luis = group["slug"], group["clients"]["Luis"]
    await close(group)
    await draw(group)
    assert (await luis.get(f"/groups/{slug}/me")).json()["revealed"] is False

    first = await reveal(luis, slug)
    second = await reveal(luis, slug)

    assert first.json() == second.json()
    assert (await luis.get(f"/groups/{slug}/me")).json()["revealed"] is True
    participants = (await luis.get(f"/groups/{slug}/participants")).json()
    seen = {p["name"]: p["has_revealed"] for p in participants}
    assert seen == {"Ana": False, "Luis": True, "Marta": False, "Pablo": False}


async def test_cannot_reveal_before_draw(group) -> None:
    await close(group)

    response = await reveal(group["clients"]["Luis"], group["slug"])

    assert response.status_code == 409


# --- repetir el sorteo ---------------------------------------------------------------------


async def test_redraw_allowed_while_nobody_has_looked(group, db: AsyncSession) -> None:
    await close(group)
    await draw(group)

    response = await draw(group)

    assert response.status_code == 200
    assert await count_assignments(db) == 4


async def test_redraw_forbidden_once_someone_has_looked(group) -> None:
    await close(group)
    await draw(group)
    await reveal(group["clients"]["Marta"], group["slug"])

    response = await draw(group)

    assert response.status_code == 409
    assert "Marta ya ha visto su resultado" in response.json()["detail"]


# --- lo que no se puede saber ---------------------------------------------------------------


async def test_nobody_learns_who_gives_to_whom(group) -> None:
    slug, clients, ids = group["slug"], group["clients"], group["ids"]
    await close(group)
    await draw(group)
    luis = clients["Luis"]

    participants = await luis.get(f"/groups/{slug}/participants")
    me = await luis.get(f"/groups/{slug}/me")
    revealed = await reveal(luis, slug)

    # En la lista solo están los datos públicos de cada persona.
    for p in participants.json():
        assert set(p) == {"id", "name", "is_admin", "has_revealed"}
    # /me no dice nada de asignaciones, solo si ya has mirado.
    assert set(me.json()) == {"id", "name", "is_admin", "wishlist", "revealed", "group"}
    # El revelado solo trae a quien regalas: ni rastro de quién te regala a ti.
    assert set(revealed.json()) == {"receiver"}
    receiver_id = revealed.json()["receiver"]["id"]
    others = set(ids.values()) - {ids["Luis"], receiver_id}
    assert not any(other in revealed.text for other in others)


# --- aviso del sorteo ----------------------------------------------------------------------


async def test_first_draw_pushes_everyone_but_the_organizer(group, sent) -> None:
    slug, clients = group["slug"], group["clients"]
    await subscribe(clients["Ana"], slug, "https://push.example/ana")
    await subscribe(clients["Luis"], slug, "https://push.example/luis")
    await close(group)

    assert (await draw(group)).status_code == 200

    assert [call["endpoint"] for call in sent] == ["https://push.example/luis"]
    assert f"/g/{slug}/revelado" in sent[0]["data"]
    # El aviso no dice a quién le regalas.
    assert not any(name in sent[0]["data"] for name in NAMES)


async def test_repeated_draw_does_not_push_again(group, sent) -> None:
    await subscribe(group["clients"]["Luis"], group["slug"])
    await close(group)
    await draw(group)

    assert (await draw(group)).status_code == 200

    assert len(sent) == 1


# --- baja después del sorteo ---------------------------------------------------------------


async def withdraw(group, name: str):
    return await group["admin"].post(
        f"/groups/{group['slug']}/participants/{group['ids'][name]}/withdraw"
    )


async def gives_to(db: AsyncSession) -> dict[str, str]:
    rows = await db.scalars(select(Assignment))
    return {str(a.giver_id): str(a.receiver_id) for a in rows}


async def test_withdraw_after_draw_keeps_a_valid_draw(group, db, sent) -> None:
    await close(group)
    await draw(group)
    before = await gives_to(db)
    luis = group["ids"]["Luis"]

    response = await withdraw(group, "Luis")

    assert response.status_code == 200
    after = await gives_to(db)
    rest = {group["ids"][n] for n in ["Ana", "Marta", "Pablo"]}
    assert set(after) == rest and set(after.values()) == rest
    assert all(giver != receiver for giver, receiver in after.items())
    # Quien le regalaba a Luis tiene destinatario nuevo y, como mucho, cambia otra persona.
    # (Si Luis y alguien se regalaban entre sí, no se puede cerrar el hueco directamente y
    # se cruza con otra pareja.)
    orphan = next(g for g, r in before.items() if r == luis)
    assert after[orphan] != luis
    changed = [g for g in after if before[g] != after[g]]
    assert orphan in changed and len(changed) <= 2
    if orphan != before[luis]:
        assert after[orphan] == before[luis]


async def test_withdrawn_person_loses_their_session(group) -> None:
    await close(group)
    await draw(group)

    await withdraw(group, "Luis")

    response = await group["clients"]["Luis"].get(f"/groups/{group['slug']}/me")
    assert response.status_code == 401


async def test_withdraw_pushes_whoever_has_a_new_person(group, db, sent) -> None:
    slug, clients = group["slug"], group["clients"]
    await close(group)
    await draw(group)
    before = await gives_to(db)
    orphan = next(g for g, r in before.items() if r == group["ids"]["Luis"])
    orphan_name = next(n for n, i in group["ids"].items() if i == orphan)
    await subscribe(clients[orphan_name], slug, "https://push.example/orphan")

    await withdraw(group, "Luis")

    assert [call["endpoint"] for call in sent] == ["https://push.example/orphan"]
    assert "/revelado" in sent[0]["data"]
    assert not any(name in sent[0]["data"] for name in ["Ana", *NAMES])


async def test_withdraw_needs_three_people_left(client, new_client) -> None:
    ana = await create_group(client)
    slug = ana["group"]["slug"]
    async with new_client() as luis, new_client() as marta:
        luis_id = (await join(luis, slug, "Luis"))["id"]
        await join(marta, slug, "Marta")
        await client.patch(f"/groups/{slug}", json={"status": "closed"})
        await client.post(f"/groups/{slug}/draw")

        response = await client.post(f"/groups/{slug}/participants/{luis_id}/withdraw")

    assert response.status_code == 422


async def test_only_admin_withdraws_and_only_after_draw(group) -> None:
    path = f"/groups/{group['slug']}/participants/{group['ids']['Marta']}/withdraw"
    assert (await group["admin"].post(path)).status_code == 409  # sin sorteo

    await close(group)
    await draw(group)

    assert (await group["clients"]["Luis"].post(path)).status_code == 403
    assert (await withdraw(group, "Ana")).status_code == 409  # el organizador no se va
