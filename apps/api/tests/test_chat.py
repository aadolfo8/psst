"""Chat anónimo (REST). Lo importante: quien recibe nunca sabe quién le regala."""

from typing import Any

from httpx import AsyncClient

from app.models import Message
from tests.conftest import a_pair, create_group


def chat_url(slug: str, role: str) -> str:
    return f"/groups/{slug}/chat/{role}"


async def reveal(client: AsyncClient, slug: str) -> None:
    assert (await client.post(f"/groups/{slug}/me/reveal")).status_code == 200


async def send(client: AsyncClient, slug: str, role: str, body: str):
    return await client.post(f"{chat_url(slug, role)}/messages", json={"body": body})


async def mark_read(client: AsyncClient, slug: str, role: str):
    return await client.post(f"{chat_url(slug, role)}/read")


async def conversation(client: AsyncClient, slug: str, role: str) -> list[dict[str, Any]]:
    response = await client.get(chat_url(slug, role))
    assert response.status_code == 200, response.text
    return response.json()["messages"]


# --- cuándo se puede chatear ----------------------------------------------------------------


async def test_no_chat_before_draw(client: AsyncClient) -> None:
    slug = (await create_group(client))["group"]["slug"]

    response = await client.get(chat_url(slug, "receiver"))

    assert response.status_code == 409


async def test_giver_side_needs_reveal_first(drawn) -> None:
    slug, luis = drawn["slug"], drawn["clients"]["Luis"]

    before = await send(luis, slug, "giver", "hola")
    await reveal(luis, slug)
    after = await send(luis, slug, "giver", "hola")

    assert before.status_code == 409
    assert "celosía" in before.json()["detail"]
    assert after.status_code == 201


async def test_receiver_side_is_open_from_the_draw(drawn) -> None:
    slug, luis = drawn["slug"], drawn["clients"]["Luis"]

    response = await send(luis, slug, "receiver", "¿quién eres?")

    assert response.status_code == 201


async def test_unknown_role_is_422(drawn) -> None:
    response = await drawn["clients"]["Luis"].get(chat_url(drawn["slug"], "admin"))

    assert response.status_code == 422


# --- mensajes -------------------------------------------------------------------------------


async def test_messages_arrive_to_the_other_side_in_order(drawn) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await reveal(giver, slug)

    await send(giver, slug, "giver", "¿qué talla usas?")
    await send(receiver, slug, "receiver", "una m")
    await send(giver, slug, "giver", "apuntado")

    giver_view = await conversation(giver, slug, "giver")
    receiver_view = await conversation(receiver, slug, "receiver")
    assert [(m["body"], m["mine"]) for m in giver_view] == [
        ("¿qué talla usas?", True),
        ("una m", False),
        ("apuntado", True),
    ]
    assert [(m["body"], m["mine"]) for m in receiver_view] == [
        ("¿qué talla usas?", False),
        ("una m", True),
        ("apuntado", False),
    ]


async def test_blank_or_too_long_messages_are_rejected(drawn) -> None:
    slug, luis = drawn["slug"], drawn["clients"]["Luis"]

    blank = await send(luis, slug, "receiver", "   ")
    too_long = await send(luis, slug, "receiver", "a" * 1001)

    assert blank.status_code == too_long.status_code == 422


async def test_each_conversation_is_separate(drawn) -> None:
    """Lo que Luis le dice a quien le regala no aparece en su chat con quien él regala."""
    slug, luis = drawn["slug"], drawn["clients"]["Luis"]
    await reveal(luis, slug)

    await send(luis, slug, "receiver", "para mi amigo invisible")
    await send(luis, slug, "giver", "para quien me ha tocado")

    assert [m["body"] for m in await conversation(luis, slug, "receiver")] == [
        "para mi amigo invisible"
    ]
    assert [m["body"] for m in await conversation(luis, slug, "giver")] == [
        "para quien me ha tocado"
    ]


# --- leídos ---------------------------------------------------------------------------------


async def test_read_marks_only_the_other_persons_messages(drawn) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await reveal(giver, slug)
    await send(giver, slug, "giver", "hola")
    await send(receiver, slug, "receiver", "hola a ti")

    response = await mark_read(receiver, slug, "receiver")

    assert response.status_code == 204
    read = {m["body"]: m["read_at"] is not None for m in await conversation(giver, slug, "giver")}
    assert read == {"hola": True, "hola a ti": False}


async def test_summary_counts_unread_per_conversation(drawn) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await reveal(giver, slug)
    await send(giver, slug, "giver", "uno")
    await send(giver, slug, "giver", "dos")

    before = (await receiver.get(f"/groups/{slug}/chat")).json()
    await mark_read(receiver, slug, "receiver")
    after = (await receiver.get(f"/groups/{slug}/chat")).json()

    assert before["as_receiver"] == 2
    assert after["as_receiver"] == 0


async def test_summary_ignores_giver_side_until_revealed(drawn) -> None:
    slug, clients = drawn["slug"], drawn["clients"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await send(receiver, slug, "receiver", "¿quién eres?")

    before = (await giver.get(f"/groups/{slug}/chat")).json()
    await reveal(giver, slug)
    after = (await giver.get(f"/groups/{slug}/chat")).json()

    assert before["as_giver"] == 0
    assert after["as_giver"] == 1


# --- lo que no se puede saber ---------------------------------------------------------------


async def test_receiver_never_sees_who_the_giver_is(drawn) -> None:
    """Todas las respuestas del lado de quien recibe, en bruto: sin rastro del id ni del
    nombre de quien le regala (ni de nadie más del grupo)."""
    slug, clients, ids = drawn["slug"], drawn["clients"], drawn["ids"]
    giver_name, receiver_name = a_pair(drawn)
    giver, receiver = clients[giver_name], clients[receiver_name]
    await reveal(giver, slug)
    await send(giver, slug, "giver", "psst")

    responses = [
        await receiver.get(chat_url(slug, "receiver")),
        await receiver.get(f"/groups/{slug}/chat"),
        await send(receiver, slug, "receiver", "¿quién eres?"),
    ]

    others = {name: id_ for name, id_ in ids.items() if name != receiver_name}
    for response in responses:
        assert not any(id_ in response.text for id_ in others.values()), response.text
        assert not any(name in response.text for name in others), response.text
    message_fields = {tuple(sorted(m)) for m in responses[0].json()["messages"]}
    assert message_fields == {("body", "created_at", "id", "mine", "read_at")}


def test_messages_table_stores_no_sender_id() -> None:
    """Ni en la base de datos hay un id de remitente que se pueda filtrar por error."""
    assert {c.name for c in Message.__table__.columns} == {
        "id",
        "assignment_id",
        "sender_role",
        "body",
        "created_at",
        "read_at",
    }
