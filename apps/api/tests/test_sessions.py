from httpx import AsyncClient

from app.security import session_cookie_name
from tests.conftest import create_group


async def test_me_without_cookie_is_401(client: AsyncClient, new_client) -> None:
    slug = (await create_group(client))["group"]["slug"]

    async with new_client() as stranger:
        response = await stranger.get(f"/groups/{slug}/me")

    assert response.status_code == 401


async def test_cookie_from_another_group_is_401(client: AsyncClient, new_client) -> None:
    slug_a = (await create_group(client))["group"]["slug"]
    async with new_client() as other:
        slug_b = (await create_group(other, name="Trabajo"))["group"]["slug"]

    # Copiamos el token del grupo A a la cookie del grupo B.
    token_a = client.cookies[session_cookie_name(slug_a)]
    async with new_client() as attacker:
        attacker.cookies.set(session_cookie_name(slug_b), token_a)
        response = await attacker.get(f"/groups/{slug_b}/me")

    assert response.status_code == 401


async def test_log_in_from_another_device(client: AsyncClient, new_client) -> None:
    me = await create_group(client)
    slug = me["group"]["slug"]

    async with new_client() as phone:
        response = await phone.post(f"/groups/{slug}/sessions", json={"name": "Ana", "pin": "1234"})
        assert response.status_code == 200
        assert response.json() == me
        assert (await phone.get(f"/groups/{slug}/me")).status_code == 200

    # La sesión del primer dispositivo sigue siendo válida.
    assert (await client.get(f"/groups/{slug}/me")).status_code == 200


async def test_log_in_ignores_name_case(client: AsyncClient, new_client) -> None:
    slug = (await create_group(client))["group"]["slug"]

    async with new_client() as phone:
        response = await phone.post(
            f"/groups/{slug}/sessions", json={"name": " aNA ", "pin": "1234"}
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Ana"


async def test_wrong_pin_and_unknown_name_give_the_same_401(
    client: AsyncClient, new_client
) -> None:
    slug = (await create_group(client))["group"]["slug"]

    async with new_client() as phone:
        wrong_pin = await phone.post(
            f"/groups/{slug}/sessions", json={"name": "Ana", "pin": "0000"}
        )
        unknown_name = await phone.post(
            f"/groups/{slug}/sessions", json={"name": "Nadie", "pin": "1234"}
        )

    assert wrong_pin.status_code == unknown_name.status_code == 401
    assert wrong_pin.json() == unknown_name.json()
