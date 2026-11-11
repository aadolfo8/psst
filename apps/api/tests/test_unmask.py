"""Apuestas y desenmascarado. Lo importante: antes de quitar las celosías nadie sabe nada de
las apuestas de los demás, y quitarlas exige escribir la frase de confirmación."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.routers.unmask import chain_order
from tests.conftest import a_pair, create_group
from tests.test_push import subscribe
from tests.test_ws import next_event, socket_of

CONFIRM = {"confirm": "desenmascarar"}


async def guess(client: AsyncClient, slug: str, guessed_id: str):
    return await client.put(f"/groups/{slug}/guess", json={"guessed_id": guessed_id})


async def unmask(client: AsyncClient, slug: str, body: dict[str, Any] = CONFIRM):
    return await client.post(f"/groups/{slug}/unmask", json=body)


# --- apuestas ------------------------------------------------------------------------------


async def test_no_guess_before_draw(client: AsyncClient) -> None:
    me = await create_group(client)
    slug = me["group"]["slug"]

    assert (await client.get(f"/groups/{slug}/guess")).status_code == 409
    assert (await guess(client, slug, me["id"])).status_code == 409


async def test_guess_and_change_it(drawn) -> None:
    slug, luis, ids = drawn["slug"], drawn["clients"]["Luis"], drawn["ids"]

    first = await guess(luis, slug, ids["Ana"])
    second = await guess(luis, slug, ids["Marta"])
    status = (await luis.get(f"/groups/{slug}/guess")).json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert status == {
        "guessed": {"id": ids["Marta"], "name": "Marta"},
        "guessers": 1,
        "participants": 4,
    }


async def test_cannot_guess_yourself_or_a_stranger(drawn, client: AsyncClient) -> None:
    slug, luis, ids = drawn["slug"], drawn["clients"]["Luis"], drawn["ids"]
    other_group = await create_group(client, name="Otro grupo")

    assert (await guess(luis, slug, ids["Luis"])).status_code == 422
    assert (await guess(luis, slug, other_group["id"])).status_code == 422


async def test_others_only_see_how_many_have_guessed(drawn) -> None:
    """Las apuestas de los demás no se ven por ningún lado: ni a quién, ni quién apostó."""
    slug, clients, ids = drawn["slug"], drawn["clients"], drawn["ids"]
    await guess(clients["Luis"], slug, ids["Marta"])
    await guess(clients["Pablo"], slug, ids["Ana"])

    marta = clients["Marta"]
    responses = [
        await marta.get(f"/groups/{slug}/guess"),
        await marta.get(f"/groups/{slug}/participants"),
        await marta.get(f"/groups/{slug}/me"),
    ]

    assert responses[0].json() == {"guessed": None, "guessers": 2, "participants": 4}
    for response in responses[1:]:
        assert "guess" not in response.text
    assert (await marta.get(f"/groups/{slug}/results")).status_code == 409


# --- quitar las celosías -------------------------------------------------------------------


async def test_only_the_admin_can_unmask(drawn) -> None:
    response = await unmask(drawn["clients"]["Luis"], drawn["slug"])

    assert response.status_code == 403


@pytest.mark.parametrize(
    "body",
    [{}, {"confirm": ""}, {"confirm": "si"}, {"confirm": "desenmascara"}],
)
async def test_unmask_needs_the_phrase(drawn, body: dict[str, Any]) -> None:
    response = await unmask(drawn["clients"]["Ana"], drawn["slug"], body)

    assert response.status_code == 422


async def test_phrase_ignores_case_and_extra_spaces(drawn) -> None:
    response = await unmask(drawn["clients"]["Ana"], drawn["slug"], {"confirm": " Desenmascarar "})

    assert response.status_code == 200
    assert response.json()["unmasked_at"] is not None


async def test_unmask_needs_a_draw_and_only_happens_once(drawn, client: AsyncClient) -> None:
    ana, slug = drawn["clients"]["Ana"], drawn["slug"]
    not_drawn = await create_group(client, name="Sin sortear")

    assert (await unmask(client, not_drawn["group"]["slug"])).status_code == 409
    assert (await unmask(ana, slug)).status_code == 200
    assert (await unmask(ana, slug)).status_code == 409


async def test_no_more_guesses_after_unmask(drawn) -> None:
    slug, clients, ids = drawn["slug"], drawn["clients"], drawn["ids"]
    await unmask(clients["Ana"], slug)

    response = await guess(clients["Luis"], slug, ids["Ana"])

    assert response.status_code == 409


# --- después: resultados y chat ------------------------------------------------------------


async def test_results_show_the_chain_and_who_guessed_right(drawn) -> None:
    slug, clients, ids, pairs = drawn["slug"], drawn["clients"], drawn["ids"], drawn["pairs"]
    giver_of = {receiver: giver for giver, receiver in pairs.items()}
    right, wrong = list(ids)[:2]
    wrong_bet = next(n for n in ids if n not in (wrong, giver_of[wrong]))
    await guess(clients[right], slug, ids[giver_of[right]])
    await guess(clients[wrong], slug, ids[wrong_bet])
    await unmask(clients["Ana"], slug)

    results = (await clients["Marta"].get(f"/groups/{slug}/results")).json()["pairs"]

    assert {p["giver"]["name"]: p["receiver"]["name"] for p in results} == pairs
    by_receiver = {p["receiver"]["name"]: p for p in results}
    assert by_receiver[right]["guessed_right"] is True
    assert by_receiver[right]["receiver_guess"]["name"] == giver_of[right]
    assert by_receiver[wrong]["guessed_right"] is False
    assert by_receiver[wrong]["receiver_guess"]["name"] == wrong_bet
    assert sum(p["guessed_right"] for p in results) == 1
    # Cadena: cada pareja empieza por quien recibía en la anterior, salvo al cerrar un círculo.
    for i, pair in enumerate(results[:-1]):
        givers_so_far = {p["giver"]["name"] for p in results[: i + 1]}
        if pair["receiver"]["name"] not in givers_so_far:
            assert results[i + 1]["giver"] == pair["receiver"]


async def test_chat_shows_the_giver_name_only_after_unmask(drawn) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    receiver = clients[receiver_name]

    before = (await receiver.get(f"/groups/{slug}/chat/receiver")).json()
    await unmask(clients["Ana"], slug)
    after = (await receiver.get(f"/groups/{slug}/chat/receiver")).json()

    assert before["giver_name"] is None
    assert after["giver_name"] == giver_name


async def test_unmask_is_pushed_live_and_by_push(drawn, sent) -> None:
    """Quien tiene el socket abierto recibe el evento; quien no, una push sin nombres."""
    slug, clients = drawn["slug"], drawn["clients"]
    assert (await subscribe(clients["Marta"], slug)).status_code in (200, 201, 204)

    async with socket_of(clients["Luis"], slug) as ws:
        await unmask(clients["Ana"], slug)
        event = await next_event(ws)

    assert event == {"type": "unmasked"}
    assert len(sent) == 1
    assert "resultados" in sent[0]["data"]
    assert not any(name in sent[0]["data"] for name in drawn["ids"])


# --- orden de la cadena --------------------------------------------------------------------


def test_chain_order_follows_who_gives_to_whom() -> None:
    a, b, c, d = "a", "b", "c", "d"

    assert chain_order({a: c, c: b, b: a}, [a, b, c]) == [a, c, b]
    # Dos círculos: a<->b y c<->d.
    assert chain_order({a: b, b: a, c: d, d: c}, [d, a, b, c]) == [d, c, a, b]
