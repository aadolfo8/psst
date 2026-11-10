"""Chat anónimo entre quien regala y quien recibe.

Cada persona tiene dos conversaciones, una por cada asignación en la que participa:
- como "giver": con la persona a la que regala (sabe quién es);
- como "receiver": con quien le regala (no sabe quién es).

El rol va en la URL y es siempre el de quien hace la petición. Los mensajes no guardan ni
devuelven ningún id de remitente, solo "mine": así la API no puede filtrar la identidad.
"""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentParticipantDep, DbSession
from app.models import Assignment, Message, Participant
from app.schemas import ChatRole, ChatSummary, Conversation, MessageCreate, MessageOut

router = APIRouter(prefix="/groups/{slug}/chat", tags=["chat"])


def other_role(role: ChatRole) -> ChatRole:
    return "receiver" if role == "giver" else "giver"


async def get_assignment(db: AsyncSession, participant: Participant, role: ChatRole) -> Assignment:
    """La asignación en la que `participant` tiene el papel `role`; 409 si no se puede chatear.

    Como giver solo a partir de abrir la celosía: si no, el chat chivaría el nombre antes
    del revelado.
    """
    me = Assignment.giver_id if role == "giver" else Assignment.receiver_id
    assignment = await db.scalar(select(Assignment).where(me == participant.id))
    if assignment is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "todavía no se ha hecho el sorteo")
    if role == "giver" and assignment.revealed_at is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "abre antes la celosía para ver a quién regalas"
        )
    return assignment


def to_message_out(message: Message, role: ChatRole) -> MessageOut:
    return MessageOut(
        id=message.id,
        mine=message.sender_role == role,
        body=message.body,
        created_at=message.created_at,
        read_at=message.read_at,
    )


async def count_unread(db: AsyncSession, assignment: Assignment | None, role: ChatRole) -> int:
    """Mensajes de la otra persona que aún no has leído."""
    if assignment is None:
        return 0
    count = await db.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.assignment_id == assignment.id,
            Message.sender_role == other_role(role),
            Message.read_at.is_(None),
        )
    )
    return count or 0


@router.get("")
async def chat_summary(current: CurrentParticipantDep, db: DbSession) -> ChatSummary:
    """Mensajes sin leer en cada conversación. Como giver solo cuenta si ya has revelado."""
    me = current.participant.id
    as_giver = await db.scalar(
        select(Assignment).where(Assignment.giver_id == me, Assignment.revealed_at.is_not(None))
    )
    as_receiver = await db.scalar(select(Assignment).where(Assignment.receiver_id == me))
    return ChatSummary(
        as_giver=await count_unread(db, as_giver, "giver"),
        as_receiver=await count_unread(db, as_receiver, "receiver"),
    )


@router.get("/{role}")
async def get_conversation(
    role: ChatRole, current: CurrentParticipantDep, db: DbSession
) -> Conversation:
    assignment = await get_assignment(db, current.participant, role)
    messages = await db.scalars(
        select(Message)
        .where(Message.assignment_id == assignment.id)
        .order_by(Message.created_at, Message.id)
    )
    return Conversation(role=role, messages=[to_message_out(m, role) for m in messages])


@router.post("/{role}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    role: ChatRole, data: MessageCreate, current: CurrentParticipantDep, db: DbSession
) -> MessageOut:
    assignment = await get_assignment(db, current.participant, role)
    message = Message(assignment_id=assignment.id, sender_role=role, body=data.body)
    db.add(message)
    await db.commit()
    await db.refresh(message)  # para tener created_at, que lo pone la base de datos
    return to_message_out(message, role)


@router.post("/{role}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(role: ChatRole, current: CurrentParticipantDep, db: DbSession) -> Response:
    """Marca como leídos todos los mensajes de la otra persona en esta conversación."""
    assignment = await get_assignment(db, current.participant, role)
    await db.execute(
        update(Message)
        .where(
            Message.assignment_id == assignment.id,
            Message.sender_role == other_role(role),
            Message.read_at.is_(None),
        )
        .values(read_at=func.now())
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
