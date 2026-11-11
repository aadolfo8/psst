from httpx import AsyncClient

from app.security import session_cookie_name
from tests.conftest import create_group, join


async def test_no_cookies_means_no_groups(client: AsyncClient) -> None:
    response = await client.get("/me/groups")

    assert response.status_code == 200
    assert response.json() == []


async def test_lists_the_groups_where_this_browser_has_a_session(client: AsyncClient) -> None:
    first = await create_group(client, name="Familia")
    second = await create_group(client, name="Oficina")

    response = await client.get("/me/groups")

    assert response.status_code == 200
    # El más nuevo primero.
    assert [group["slug"] for group in response.json()] == [
        second["group"]["slug"],
        first["group"]["slug"],
    ]


async def test_does_not_list_groups_of_other_browsers(client: AsyncClient, new_client) -> None:
    mine = await create_group(client, name="Familia")
    async with new_client() as other:
        await create_group(other, name="De otra persona")

        response = await client.get("/me/groups")

    assert [group["slug"] for group in response.json()] == [mine["group"]["slug"]]


async def test_includes_groups_joined_with_a_pin(client: AsyncClient, new_client) -> None:
    ana = await create_group(client)
    async with new_client() as luis:
        await join(luis, ana["group"]["slug"], "Luis")

        response = await luis.get("/me/groups")

    assert [group["slug"] for group in response.json()] == [ana["group"]["slug"]]


async def test_ignores_a_cookie_that_belongs_to_another_group(
    client: AsyncClient, new_client
) -> None:
    """Un token válido en el grupo A no sirve poniéndolo en la cookie del grupo B."""
    mine = await create_group(client, name="Familia")
    async with new_client() as other:
        theirs = await create_group(other, name="De otra persona")
        stolen = client.cookies[session_cookie_name(mine["group"]["slug"])]
        other.cookies.set(session_cookie_name(theirs["group"]["slug"]), stolen)

        response = await other.get("/me/groups")

    assert [group["slug"] for group in response.json()] == []


async def test_ignores_invalid_tokens_and_unrelated_cookies(client: AsyncClient) -> None:
    client.cookies.set("psst_abcdefghjk", "no-es-un-token")
    client.cookies.set("otra_cookie", "valor")

    response = await client.get("/me/groups")

    assert response.json() == []
