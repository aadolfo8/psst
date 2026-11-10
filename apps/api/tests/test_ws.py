"""Websocket del chat: lo que se empuja a cada lado y lo que no se puede saber por él."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import AsyncClient
from httpx_ws import AsyncWebSocketSession, WebSocketDisconnect, WebSocketUpgradeError, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from app.main import app
from tests.conftest import a_pair

TIMEOUT = 3


@asynccontextmanager
async def socket_of(client: AsyncClient, slug: str, **kwargs: Any) -> AsyncIterator[Any]:
    """Abre el websocket con las cookies (la sesión) de `client`."""
    transport = ASGIWebSocketTransport(app=app)
    async with (
        AsyncClient(
            transport=transport, base_url="http://test", cookies=client.cookies
        ) as ws_client,
        aconnect_ws(f"/groups/{slug}/ws", ws_client, **kwargs) as ws,
    ):
        yield ws


async def is_rejected(client: AsyncClient, slug: str, **kwargs: Any) -> bool:
    """True si el servidor cierra el socket sin aceptarlo (código 1008)."""
    rejected = False
    try:
        async with socket_of(client, slug, **kwargs):
            pass
    # except*: httpx-ws a veces envuelve el error en un ExceptionGroup.
    except* (WebSocketDisconnect, WebSocketUpgradeError):
        rejected = True
    return rejected


async def send(client: AsyncClient, slug: str, role: str, body: str) -> dict[str, Any]:
    response = await client.post(f"/groups/{slug}/chat/{role}/messages", json={"body": body})
    assert response.status_code == 201, response.text
    return response.json()


async def next_event(ws: AsyncWebSocketSession) -> dict[str, Any]:
    return await ws.receive_json(timeout=TIMEOUT)


# --- quién puede conectarse -----------------------------------------------------------------


async def test_rejects_without_session(new_client, drawn) -> None:
    async with new_client() as stranger:
        assert await is_rejected(stranger, drawn["slug"])


async def test_rejects_another_origin(drawn) -> None:
    luis = drawn["clients"]["Luis"]
    assert await is_rejected(luis, drawn["slug"], headers={"origin": "https://otra-web.example"})
    assert not await is_rejected(luis, drawn["slug"], headers={"origin": "http://localhost:3000"})


# --- eventos --------------------------------------------------------------------------------


async def test_message_is_pushed_to_the_other_side(drawn) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await giver.post(f"/groups/{slug}/me/reveal")

    async with socket_of(receiver, slug) as ws:
        sent = await send(giver, slug, "giver", "psst")
        event = await next_event(ws)

    assert event["type"] == "message"
    assert event["role"] == "receiver"
    assert event["message"]["id"] == sent["id"]
    assert event["message"]["body"] == "psst"
    assert event["message"]["mine"] is False


async def test_read_and_typing_are_pushed(drawn) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await giver.post(f"/groups/{slug}/me/reveal")
    await send(giver, slug, "giver", "hola")

    async with socket_of(giver, slug) as giver_ws, socket_of(receiver, slug) as receiver_ws:
        await receiver.post(f"/groups/{slug}/chat/receiver/read")
        read = await next_event(giver_ws)
        await giver_ws.send_json({"type": "typing", "role": "giver"})
        typing = await next_event(receiver_ws)

    assert read == {"type": "read", "role": "giver"}
    assert typing == {"type": "typing", "role": "receiver"}


async def test_typing_before_reveal_goes_nowhere(drawn) -> None:
    """Sin abrir la celosía no hay conversación como giver: el evento se ignora."""
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]

    async with socket_of(giver, slug) as giver_ws, socket_of(receiver, slug) as receiver_ws:
        await giver_ws.send_json({"type": "typing", "role": "giver"})
        await giver_ws.send_json("esto no es un evento")
        with pytest.raises(TimeoutError):
            await receiver_ws.receive_json(timeout=0.5)


# --- lo que no se puede saber ---------------------------------------------------------------


async def test_receiver_events_carry_no_identity(drawn) -> None:
    slug, clients, ids = drawn["slug"], drawn["clients"], drawn["ids"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await giver.post(f"/groups/{slug}/me/reveal")

    async with socket_of(receiver, slug) as ws:
        await send(giver, slug, "giver", "¿qué talla usas?")
        await giver.post(f"/groups/{slug}/chat/giver/read")
        events = [await next_event(ws), await next_event(ws)]

    others = {name: id_ for name, id_ in ids.items() if name != receiver_name}
    for event in events:
        text = str(event)
        assert not any(id_ in text for id_ in others.values()), event
        assert not any(name in text for name in others), event
    assert set(events[0]["message"]) == {"id", "mine", "body", "created_at", "read_at"}
