from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group
from tests.conftest import create_group, join


@pytest.fixture
async def lobby(client: AsyncClient, new_client) -> Any:
    """Grupo con Ana (organizadora, `client`), Luis y Marta. Devuelve slug, ids y clientes."""
    ana = await create_group(client)
    slug = ana["group"]["slug"]
    async with new_client() as luis_client, new_client() as marta_client:
        luis = await join(luis_client, slug, "Luis")
        marta = await join(marta_client, slug, "Marta")
        yield {
            "slug": slug,
            "ana": ana["id"],
            "luis": luis["id"],
            "marta": marta["id"],
            "admin": client,
            "luis_client": luis_client,
        }


async def set_status(db: AsyncSession, slug: str, group_status: str) -> None:
    await db.execute(update(Group).where(Group.slug == slug).values(status=group_status))
    await db.commit()


# --- apuntados -------------------------------------------------------------------------


async def test_participants_requires_session(lobby, new_client) -> None:
    async with new_client() as stranger:
        response = await stranger.get(f"/groups/{lobby['slug']}/participants")

    assert response.status_code == 401


async def test_participants_in_join_order_without_private_data(lobby) -> None:
    await lobby["luis_client"].put(
        f"/groups/{lobby['slug']}/me/wishlist", json={"wishlist": "libros"}
    )

    response = await lobby["luis_client"].get(f"/groups/{lobby['slug']}/participants")

    assert response.status_code == 200
    assert response.json() == [
        {"id": lobby["ana"], "name": "Ana", "is_admin": True},
        {"id": lobby["luis"], "name": "Luis", "is_admin": False},
        {"id": lobby["marta"], "name": "Marta", "is_admin": False},
    ]


# --- lista de deseos -------------------------------------------------------------------


async def test_update_own_wishlist(lobby) -> None:
    luis = lobby["luis_client"]
    slug = lobby["slug"]

    response = await luis.put(f"/groups/{slug}/me/wishlist", json={"wishlist": "  café y libros "})

    assert response.status_code == 200
    assert response.json()["wishlist"] == "café y libros"
    assert (await luis.get(f"/groups/{slug}/me")).json()["wishlist"] == "café y libros"


async def test_wishlist_too_long_is_422(lobby) -> None:
    response = await lobby["luis_client"].put(
        f"/groups/{lobby['slug']}/me/wishlist", json={"wishlist": "x" * 1001}
    )

    assert response.status_code == 422


async def test_wishlist_requires_session(lobby, new_client) -> None:
    async with new_client() as stranger:
        response = await stranger.put(
            f"/groups/{lobby['slug']}/me/wishlist", json={"wishlist": "hola"}
        )

    assert response.status_code == 401


# --- exclusiones -----------------------------------------------------------------------


async def test_admin_creates_and_lists_exclusions(lobby) -> None:
    admin, slug = lobby["admin"], lobby["slug"]

    created = await admin.post(
        f"/groups/{slug}/exclusions",
        json={"participant_a_id": lobby["luis"], "participant_b_id": lobby["marta"]},
    )
    listed = await admin.get(f"/groups/{slug}/exclusions")

    assert created.status_code == 201
    exclusion = created.json()
    assert {exclusion["participant_a"]["name"], exclusion["participant_b"]["name"]} == {
        "Luis",
        "Marta",
    }
    assert listed.json() == [exclusion]


async def test_non_admin_cannot_manage_exclusions(lobby) -> None:
    luis, slug = lobby["luis_client"], lobby["slug"]
    pair = {"participant_a_id": lobby["ana"], "participant_b_id": lobby["marta"]}
    created = await lobby["admin"].post(f"/groups/{slug}/exclusions", json=pair)

    assert (await luis.get(f"/groups/{slug}/exclusions")).status_code == 403
    assert (await luis.post(f"/groups/{slug}/exclusions", json=pair)).status_code == 403
    delete = await luis.delete(f"/groups/{slug}/exclusions/{created.json()['id']}")
    assert delete.status_code == 403


async def test_exclusion_with_same_person_is_422(lobby) -> None:
    response = await lobby["admin"].post(
        f"/groups/{lobby['slug']}/exclusions",
        json={"participant_a_id": lobby["luis"], "participant_b_id": lobby["luis"]},
    )

    assert response.status_code == 422


async def test_exclusion_with_someone_from_another_group_is_404(lobby, new_client) -> None:
    async with new_client() as other:
        outsider = await create_group(other, name="Trabajo", admin_name="Pepe")

    response = await lobby["admin"].post(
        f"/groups/{lobby['slug']}/exclusions",
        json={"participant_a_id": lobby["luis"], "participant_b_id": outsider["id"]},
    )

    assert response.status_code == 404


async def test_reversed_duplicate_exclusion_is_409(lobby) -> None:
    admin, slug = lobby["admin"], lobby["slug"]
    await admin.post(
        f"/groups/{slug}/exclusions",
        json={"participant_a_id": lobby["luis"], "participant_b_id": lobby["marta"]},
    )

    response = await admin.post(
        f"/groups/{slug}/exclusions",
        json={"participant_a_id": lobby["marta"], "participant_b_id": lobby["luis"]},
    )

    assert response.status_code == 409


async def test_delete_exclusion(lobby, new_client) -> None:
    admin, slug = lobby["admin"], lobby["slug"]
    created = await admin.post(
        f"/groups/{slug}/exclusions",
        json={"participant_a_id": lobby["luis"], "participant_b_id": lobby["marta"]},
    )
    exclusion_id = created.json()["id"]

    assert (await admin.delete(f"/groups/{slug}/exclusions/{exclusion_id}")).status_code == 204
    assert (await admin.get(f"/groups/{slug}/exclusions")).json() == []
    assert (await admin.delete(f"/groups/{slug}/exclusions/{exclusion_id}")).status_code == 404


async def test_cannot_delete_exclusion_of_another_group(lobby, new_client) -> None:
    async with new_client() as pepe, new_client() as rosa_client:
        other = await create_group(pepe, name="Trabajo", admin_name="Pepe")
        other_slug = other["group"]["slug"]
        rosa = await join(rosa_client, other_slug, "Rosa")
        created = await pepe.post(
            f"/groups/{other_slug}/exclusions",
            json={"participant_a_id": other["id"], "participant_b_id": rosa["id"]},
        )

    # Ana es organizadora de su grupo, pero la exclusión es del grupo de Pepe.
    response = await lobby["admin"].delete(
        f"/groups/{lobby['slug']}/exclusions/{created.json()['id']}"
    )

    assert response.status_code == 404


async def test_exclusions_are_frozen_after_draw(lobby, db: AsyncSession) -> None:
    admin, slug = lobby["admin"], lobby["slug"]
    created = await admin.post(
        f"/groups/{slug}/exclusions",
        json={"participant_a_id": lobby["luis"], "participant_b_id": lobby["marta"]},
    )
    await set_status(db, slug, "drawn")

    new = await admin.post(
        f"/groups/{slug}/exclusions",
        json={"participant_a_id": lobby["ana"], "participant_b_id": lobby["luis"]},
    )
    delete = await admin.delete(f"/groups/{slug}/exclusions/{created.json()['id']}")

    assert new.status_code == 409
    assert delete.status_code == 409


# --- cerrar y reabrir inscripciones ----------------------------------------------------


async def test_admin_closes_and_reopens_registrations(lobby, new_client) -> None:
    admin, slug = lobby["admin"], lobby["slug"]

    closed = await admin.patch(f"/groups/{slug}", json={"status": "closed"})
    async with new_client() as late:
        rejected = await late.post(
            f"/groups/{slug}/participants", json={"name": "Pablo", "pin": "1111"}
        )
        reopened = await admin.patch(f"/groups/{slug}", json={"status": "open"})
        accepted = await late.post(
            f"/groups/{slug}/participants", json={"name": "Pablo", "pin": "1111"}
        )

    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert rejected.status_code == 409
    assert reopened.json()["status"] == "open"
    assert accepted.status_code == 201


async def test_non_admin_cannot_change_status(lobby) -> None:
    response = await lobby["luis_client"].patch(
        f"/groups/{lobby['slug']}", json={"status": "closed"}
    )

    assert response.status_code == 403


async def test_status_cannot_be_set_to_drawn_by_hand(lobby) -> None:
    response = await lobby["admin"].patch(f"/groups/{lobby['slug']}", json={"status": "drawn"})

    assert response.status_code == 422


async def test_status_cannot_change_after_draw(lobby, db: AsyncSession) -> None:
    await set_status(db, lobby["slug"], "drawn")

    response = await lobby["admin"].patch(f"/groups/{lobby['slug']}", json={"status": "open"})

    assert response.status_code == 409
