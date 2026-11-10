"""Sala de espera: apuntados, lista de deseos, exclusiones y cierre de inscripciones."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.deps import CurrentAdminDep, CurrentParticipantDep, DbSession
from app.models import Exclusion, Group, Participant
from app.routers.groups import build_me
from app.schemas import (
    ExclusionCreate,
    ExclusionOut,
    GroupPublic,
    GroupStatusUpdate,
    Me,
    ParticipantPublic,
    ParticipantRef,
    WishlistUpdate,
)

router = APIRouter(prefix="/groups/{slug}", tags=["lobby"])


def ensure_not_drawn(group: Group) -> None:
    if group.status == "drawn":
        raise HTTPException(status.HTTP_409_CONFLICT, "el sorteo ya está hecho")


@router.get("/participants")
async def list_participants(
    current: CurrentParticipantDep, db: DbSession
) -> list[ParticipantPublic]:
    participants = await db.scalars(
        select(Participant)
        .where(Participant.group_id == current.group.id)
        .order_by(Participant.created_at, Participant.id)
    )
    return [
        ParticipantPublic(id=p.id, name=p.name, is_admin=p.id == current.group.admin_participant_id)
        for p in participants
    ]


@router.put("/me/wishlist")
async def update_wishlist(
    data: WishlistUpdate, current: CurrentParticipantDep, db: DbSession
) -> Me:
    # Solo existe la ruta /me: nadie puede editar la lista de otra persona.
    current.participant.wishlist = data.wishlist
    await db.commit()
    return build_me(current.participant, current.group)


@router.patch("")
async def update_group_status(
    data: GroupStatusUpdate, current: CurrentAdminDep, db: DbSession
) -> GroupPublic:
    """Cierra o reabre las inscripciones."""
    ensure_not_drawn(current.group)
    current.group.status = data.status
    await db.commit()
    return GroupPublic.model_validate(current.group)


@router.get("/exclusions")
async def list_exclusions(current: CurrentAdminDep, db: DbSession) -> list[ExclusionOut]:
    a = aliased(Participant)
    b = aliased(Participant)
    rows = await db.execute(
        select(Exclusion.id, a.id, a.name, b.id, b.name)
        .join(a, a.id == Exclusion.participant_a_id)
        .join(b, b.id == Exclusion.participant_b_id)
        .where(Exclusion.group_id == current.group.id)
        .order_by(Exclusion.created_at)
    )
    return [
        ExclusionOut(
            id=exclusion_id,
            participant_a=ParticipantRef(id=a_id, name=a_name),
            participant_b=ParticipantRef(id=b_id, name=b_name),
        )
        for exclusion_id, a_id, a_name, b_id, b_name in rows
    ]


@router.post("/exclusions", status_code=status.HTTP_201_CREATED)
async def create_exclusion(
    data: ExclusionCreate, current: CurrentAdminDep, db: DbSession
) -> ExclusionOut:
    ensure_not_drawn(current.group)

    participants = (
        await db.scalars(
            select(Participant).where(
                Participant.group_id == current.group.id,
                Participant.id.in_([data.participant_a_id, data.participant_b_id]),
            )
        )
    ).all()
    if len(participants) != 2:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "esa persona no está en el grupo")

    # La pareja se guarda ordenada (ver el modelo Exclusion).
    a, b = sorted(participants, key=lambda p: p.id)
    exclusion = Exclusion(group_id=current.group.id, participant_a_id=a.id, participant_b_id=b.id)
    db.add(exclusion)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "esa exclusión ya existe") from None

    return ExclusionOut(
        id=exclusion.id,
        participant_a=ParticipantRef(id=a.id, name=a.name),
        participant_b=ParticipantRef(id=b.id, name=b.name),
    )


@router.delete("/exclusions/{exclusion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exclusion(
    exclusion_id: uuid.UUID, current: CurrentAdminDep, db: DbSession
) -> Response:
    ensure_not_drawn(current.group)

    exclusion = await db.scalar(
        select(Exclusion).where(
            Exclusion.id == exclusion_id, Exclusion.group_id == current.group.id
        )
    )
    if exclusion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "esa exclusión no existe")

    await db.delete(exclusion)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
