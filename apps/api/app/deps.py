from typing import Annotated, NamedTuple

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Group, Participant, ParticipantSession
from app.security import hash_token, session_cookie_name

DbSession = Annotated[AsyncSession, Depends(get_session)]


class CurrentParticipant(NamedTuple):
    participant: Participant
    group: Group


async def get_current_participant(slug: str, request: Request, db: DbSession) -> CurrentParticipant:
    """Participante dueño de la cookie de sesión de este grupo; 401 si no hay sesión válida."""
    not_authenticated = HTTPException(status.HTTP_401_UNAUTHORIZED, "no has entrado en este grupo")

    token = request.cookies.get(session_cookie_name(slug))
    if not token:
        raise not_authenticated

    row = (
        await db.execute(
            select(ParticipantSession, Participant, Group)
            .join(Participant, Participant.id == ParticipantSession.participant_id)
            .join(Group, Group.id == Participant.group_id)
            # Filtrar también por slug: un token de otro grupo no sirve aquí.
            .where(ParticipantSession.token_hash == hash_token(token), Group.slug == slug)
        )
    ).first()
    if row is None:
        raise not_authenticated

    session, participant, group = row
    session.last_seen_at = func.now()
    await db.commit()
    return CurrentParticipant(participant, group)


CurrentParticipantDep = Annotated[CurrentParticipant, Depends(get_current_participant)]


async def get_current_admin(current: CurrentParticipantDep) -> CurrentParticipant:
    """Como get_current_participant, pero solo deja pasar al organizador del grupo."""
    if current.group.admin_participant_id != current.participant.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "solo el organizador puede hacer esto")
    return current


CurrentAdminDep = Annotated[CurrentParticipant, Depends(get_current_admin)]
