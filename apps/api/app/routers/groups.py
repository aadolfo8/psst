import math
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import CurrentParticipantDep, DbSession
from app.models import Group, Participant, ParticipantSession
from app.schemas import GroupCreate, GroupPublic, Me, ParticipantCredentials
from app.security import (
    LOCKOUT_DURATION,
    MAX_FAILED_ATTEMPTS,
    SESSION_MAX_AGE_SECONDS,
    hash_pin,
    hash_token,
    new_session_token,
    new_slug,
    session_cookie_name,
    verify_pin,
)

router = APIRouter(prefix="/groups", tags=["groups"])

# Mismo mensaje si el nombre no existe o si el PIN es incorrecto.
WRONG_CREDENTIALS = "nombre o PIN incorrectos"


async def get_group_or_404(db: AsyncSession, slug: str) -> Group:
    group = await db.scalar(select(Group).where(Group.slug == slug))
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no existe ningún grupo con ese enlace")
    return group


def open_session(db: AsyncSession, participant: Participant) -> str:
    """Crea una sesión para el participante y devuelve el token (que solo viaja en la cookie)."""
    token = new_session_token()
    db.add(ParticipantSession(participant_id=participant.id, token_hash=hash_token(token)))
    return token


def set_session_cookie(response: Response, slug: str, token: str) -> None:
    response.set_cookie(
        session_cookie_name(slug),
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
    )


def build_me(participant: Participant, group: Group) -> Me:
    return Me(
        id=participant.id,
        name=participant.name,
        is_admin=group.admin_participant_id == participant.id,
        wishlist=participant.wishlist,
        group=GroupPublic.model_validate(group),
    )


def locked_error(locked_until: datetime, now: datetime) -> HTTPException:
    seconds = math.ceil((locked_until - now).total_seconds())
    minutes = math.ceil(seconds / 60)
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        f"demasiados intentos; vuelve a probar en {minutes} min",
        headers={"Retry-After": str(seconds)},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(data: GroupCreate, response: Response, db: DbSession) -> Me:
    """Crea el grupo y al organizador, que también participa, y abre su sesión."""
    group = Group(
        slug=new_slug(),
        name=data.name,
        budget=data.budget,
        exchange_date=data.exchange_date,
    )
    db.add(group)
    await db.flush()  # para tener group.id

    admin = Participant(group_id=group.id, name=data.admin_name, pin_hash=await hash_pin(data.pin))
    db.add(admin)
    await db.flush()  # para tener admin.id
    group.admin_participant_id = admin.id

    token = open_session(db, admin)
    await db.commit()

    set_session_cookie(response, group.slug, token)
    return build_me(admin, group)


@router.get("/{slug}")
async def get_group(slug: str, db: DbSession) -> GroupPublic:
    """Lo mínimo para la pantalla de unirse. No incluye a los participantes."""
    return GroupPublic.model_validate(await get_group_or_404(db, slug))


@router.post("/{slug}/participants", status_code=status.HTTP_201_CREATED)
async def join_group(
    slug: str, data: ParticipantCredentials, response: Response, db: DbSession
) -> Me:
    group = await get_group_or_404(db, slug)
    if group.status != "open":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "las inscripciones de este grupo están cerradas"
        )

    participant = Participant(group_id=group.id, name=data.name, pin_hash=await hash_pin(data.pin))
    db.add(participant)
    try:
        await db.flush()
    except IntegrityError:
        # Lo garantiza el índice único (group_id, lower(name)), también si dos personas
        # se unen con el mismo nombre a la vez.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "ya hay alguien con ese nombre en el grupo; si eres tú, entra con tu PIN",
        ) from None

    token = open_session(db, participant)
    await db.commit()

    set_session_cookie(response, slug, token)
    return build_me(participant, group)


@router.post("/{slug}/sessions")
async def log_in(slug: str, data: ParticipantCredentials, response: Response, db: DbSession) -> Me:
    """Recupera la sesión con nombre + PIN, por ejemplo desde otro dispositivo."""
    group = await get_group_or_404(db, slug)

    # FOR UPDATE bloquea la fila hasta el commit: varios intentos a la vez se procesan
    # de uno en uno y nadie se salta el límite de fallos.
    participant = await db.scalar(
        select(Participant)
        .where(
            Participant.group_id == group.id,
            func.lower(Participant.name) == func.lower(data.name),
        )
        .with_for_update()
    )
    if participant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, WRONG_CREDENTIALS)

    now = datetime.now(UTC)
    # Bloqueado: no se mira el PIN, ni siquiera si es el correcto.
    if participant.locked_until is not None and participant.locked_until > now:
        raise locked_error(participant.locked_until, now)

    if not await verify_pin(participant.pin_hash, data.pin):
        participant.failed_attempts += 1
        if participant.failed_attempts >= MAX_FAILED_ATTEMPTS:
            participant.failed_attempts = 0
            participant.locked_until = now + LOCKOUT_DURATION
            await db.commit()
            raise locked_error(participant.locked_until, now)
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, WRONG_CREDENTIALS)

    participant.failed_attempts = 0
    participant.locked_until = None
    token = open_session(db, participant)
    await db.commit()

    set_session_cookie(response, slug, token)
    return build_me(participant, group)


@router.get("/{slug}/me")
async def get_me(current: CurrentParticipantDep) -> Me:
    return build_me(current.participant, current.group)
