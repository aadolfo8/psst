"""Notificaciones push: suscripciones y cuándo se envían.

No se habla con ningún servicio de push: se sustituye `webpush` por una función que apunta
lo que se le pide enviar.
"""

from httpx import AsyncClient
from pywebpush import WebPushException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import push
from app.config import get_settings
from app.models import PushSubscription
from tests.conftest import a_pair, create_group
from tests.test_ws import socket_of

SUBSCRIPTION = {
    "endpoint": "https://push.example/abc",
    "keys": {"p256dh": "clave-p256dh", "auth": "clave-auth"},
}


async def subscribe(client: AsyncClient, slug: str, endpoint: str = SUBSCRIPTION["endpoint"]):
    body = SUBSCRIPTION | {"endpoint": endpoint}
    return await client.put(f"/groups/{slug}/me/push", json=body)


async def count_subscriptions(db: AsyncSession) -> int:
    return await db.scalar(select(func.count()).select_from(PushSubscription))


# --- configuración y suscripciones ---------------------------------------------------------


async def test_public_key_is_404_until_configured(client: AsyncClient, monkeypatch) -> None:
    missing = await client.get("/push/public-key")
    monkeypatch.setattr(get_settings(), "vapid_private_key", "privada")
    monkeypatch.setattr(get_settings(), "vapid_public_key", "publica")
    configured = await client.get("/push/public-key")

    assert missing.status_code == 404
    assert configured.json() == {"public_key": "publica"}


async def test_subscribe_twice_keeps_one_and_delete_removes_it(
    client: AsyncClient, db: AsyncSession
) -> None:
    slug = (await create_group(client))["group"]["slug"]

    first = await subscribe(client, slug)
    second = await subscribe(client, slug)
    assert first.status_code == second.status_code == 204
    assert await count_subscriptions(db) == 1

    deleted = await client.request("DELETE", f"/groups/{slug}/me/push", json=SUBSCRIPTION)
    assert deleted.status_code == 204
    assert await count_subscriptions(db) == 0


async def test_subscription_needs_session_and_https_endpoint(
    client: AsyncClient, new_client
) -> None:
    slug = (await create_group(client))["group"]["slug"]

    async with new_client() as stranger:
        no_session = await subscribe(stranger, slug)
    insecure = await subscribe(client, slug, endpoint="http://push.example/abc")

    assert no_session.status_code == 401
    assert insecure.status_code == 422


# --- cuándo se envía -------------------------------------------------------------------------


async def test_message_to_someone_offline_sends_a_push(drawn, sent) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await giver.post(f"/groups/{slug}/me/reveal")
    await subscribe(receiver, slug)

    await giver.post(f"/groups/{slug}/chat/giver/messages", json={"body": "¿talla?"})

    assert len(sent) == 1
    assert sent[0]["endpoint"] == SUBSCRIPTION["endpoint"]
    assert '"¿talla?"' in sent[0]["data"]
    assert "tu amigo invisible" in sent[0]["data"]


async def test_no_push_while_the_chat_is_open(drawn, sent) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await giver.post(f"/groups/{slug}/me/reveal")
    await subscribe(receiver, slug)

    async with socket_of(receiver, slug) as ws:
        await giver.post(f"/groups/{slug}/chat/giver/messages", json={"body": "hola"})
        event = await ws.receive_json(timeout=3)

    assert event["type"] == "message"
    assert sent == []


async def test_push_to_the_giver_never_names_the_receiver(drawn, sent) -> None:
    """Quien regala puede no haber abierto aún la celosía: el aviso no dice a quién regala."""
    slug, clients, ids = drawn["slug"], drawn["clients"], drawn["ids"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await subscribe(giver, slug)

    await receiver.post(f"/groups/{slug}/chat/receiver/messages", json={"body": "¿quién eres?"})

    assert len(sent) == 1
    data = sent[0]["data"]
    assert "a quien regalas" in data
    assert not any(name in data for name in ids)
    assert not any(id_ in data for id_ in ids.values())


async def test_gone_subscriptions_are_forgotten(drawn, sent, monkeypatch, db: AsyncSession) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await giver.post(f"/groups/{slug}/me/reveal")
    await subscribe(receiver, slug)

    class Gone:
        status_code = 410

    def gone_webpush(*args, **kwargs):
        raise WebPushException("gone", response=Gone())

    monkeypatch.setattr(push, "webpush", gone_webpush)
    response = await giver.post(f"/groups/{slug}/chat/giver/messages", json={"body": "hola"})

    assert response.status_code == 201  # el mensaje se guarda igual
    assert await count_subscriptions(db) == 0


async def test_without_vapid_keys_nothing_is_sent(drawn, monkeypatch) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await giver.post(f"/groups/{slug}/me/reveal")
    await subscribe(receiver, slug)

    def must_not_be_called(*args, **kwargs):
        raise AssertionError("no hay claves: no debería enviarse nada")

    monkeypatch.setattr(push, "webpush", must_not_be_called)
    response = await giver.post(f"/groups/{slug}/chat/giver/messages", json={"body": "hola"})

    assert response.status_code == 201
