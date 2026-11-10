"""Websocket del chat: una conexión por participante.

Por ella el servidor empuja lo que pasa en sus dos conversaciones:
  {"type": "message", "role": <tu papel>, "message": {...}}   alguien te ha escrito
  {"type": "read", "role": <tu papel>}                        han leído tus mensajes
  {"type": "typing", "role": <tu papel>}                      la otra persona escribe

Y el cliente solo manda una cosa:
  {"type": "typing", "role": <tu papel>}                      estoy escribiendo

Enviar mensajes y marcar leídos va por REST (routers/chat.py), que es quien emite los
eventos. Los eventos solo llevan el papel y el mensaje, nunca ids ni nombres.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.db import SessionLocal
from app.deps import find_session
from app.models import Participant
from app.realtime import manager
from app.routers.chat import counterpart_id, other_role
from app.schemas import ChatRole
from app.security import session_cookie_name

router = APIRouter(tags=["chat"])


class TypingEvent(BaseModel):
    type: str
    role: ChatRole


@router.websocket("/groups/{slug}/ws")
async def chat_socket(slug: str, websocket: WebSocket) -> None:
    participant = await authenticate(slug, websocket)
    if participant is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    manager.connect(participant.id, websocket)
    try:
        while True:
            await handle_typing(participant, await websocket.receive_json())
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(participant.id, websocket)


async def authenticate(slug: str, websocket: WebSocket) -> Participant | None:
    """La misma cookie de sesión que el resto de la API, más una comprobación del Origin.

    Los navegadores mandan la cookie en el handshake desde cualquier web, así que sin mirar
    el Origin otra página podría abrir el socket con tu sesión.
    """
    origin = websocket.headers.get("origin")
    if origin is not None and origin != get_settings().web_origin:
        return None

    token = websocket.cookies.get(session_cookie_name(slug))
    if not token:
        return None
    async with SessionLocal() as db:
        found = await find_session(db, slug, token)
        return found.participant if found else None


async def handle_typing(participant: Participant, payload: object) -> None:
    """Reenvía "escribiendo…" a la otra persona de esa conversación; lo demás se ignora."""
    try:
        event = TypingEvent.model_validate(payload)
    except ValidationError:
        return
    if event.type != "typing":
        return
    async with SessionLocal() as db:
        try:
            other = await counterpart_id(db, participant, event.role)
        except HTTPException:  # sin sorteo o sin revelar: no hay con quién hablar
            return
    await manager.send(other, {"type": "typing", "role": other_role(event.role)})
