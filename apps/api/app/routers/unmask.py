"""Apuestas y desenmascarado.

Mientras las celosías están puestas, cada persona apuesta quién cree que le regala. Nadie ve
las apuestas de los demás, solo cuántas hay. Cuando el organizador quita las celosías (no se
puede deshacer), todos ven quién les regalaba y se publica quién acertó.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentAdminDep, CurrentParticipant, CurrentParticipantDep, DbSession
from app.models import Assignment, Group, Guess, Participant
from app.push import notify
from app.realtime import manager
from app.schemas import (
    GroupPublic,
    GuessStatus,
    GuessUpdate,
    ParticipantRef,
    ResultPair,
    Results,
    UnmaskRequest,
)

router = APIRouter(prefix="/groups/{slug}", tags=["unmask"])


def ensure_drawn(group: Group) -> None:
    if group.status != "drawn":
        raise HTTPException(status.HTTP_409_CONFLICT, "todavía no se ha hecho el sorteo")


def ensure_masked(group: Group) -> None:
    if group.unmasked_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "ya se han quitado las celosías")


async def guess_status(db: AsyncSession, current: CurrentParticipant) -> GuessStatus:
    guessed = (
        await db.execute(
            select(Participant.id, Participant.name)
            .join(Guess, Guess.guessed_id == Participant.id)
            .where(Guess.guesser_id == current.participant.id)
        )
    ).first()
    guessers = await db.scalar(
        select(func.count()).select_from(Guess).where(Guess.group_id == current.group.id)
    )
    participants = await db.scalar(
        select(func.count())
        .select_from(Participant)
        .where(Participant.group_id == current.group.id)
    )
    return GuessStatus(
        guessed=ParticipantRef(id=guessed.id, name=guessed.name) if guessed else None,
        guessers=guessers or 0,
        participants=participants or 0,
    )


@router.get("/guess")
async def get_guess(current: CurrentParticipantDep, db: DbSession) -> GuessStatus:
    ensure_drawn(current.group)
    return await guess_status(db, current)


@router.put("/guess")
async def put_guess(
    data: GuessUpdate, current: CurrentParticipantDep, db: DbSession
) -> GuessStatus:
    """Apuesta (o cambia la apuesta) por quién te regala."""
    # FOR SHARE: si el organizador está quitando las celosías justo ahora (FOR UPDATE), la
    # apuesta espera a que termine y ve el grupo ya desenmascarado; no se cuela después.
    group = await db.scalar(
        select(Group)
        .where(Group.id == current.group.id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    assert group is not None
    ensure_drawn(group)
    ensure_masked(group)
    if data.guessed_id == current.participant.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "no te regalas a ti")
    in_group = await db.scalar(
        select(Participant.id).where(
            Participant.id == data.guessed_id, Participant.group_id == current.group.id
        )
    )
    if in_group is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "esa persona no está en el grupo"
        )

    # Insertar o, si ya había apuesta, cambiarla. En una sola sentencia: dos peticiones a la
    # vez no pueden dejar dos apuestas de la misma persona.
    await db.execute(
        insert(Guess)
        .values(
            group_id=current.group.id,
            guesser_id=current.participant.id,
            guessed_id=data.guessed_id,
        )
        .on_conflict_do_update(
            constraint="uq_guesses_guesser_id",
            set_={"guessed_id": data.guessed_id, "updated_at": func.now()},
        )
    )
    await db.commit()
    return await guess_status(db, current)


@router.post("/unmask")
async def unmask(data: UnmaskRequest, current: CurrentAdminDep, db: DbSession) -> GroupPublic:
    """Quita las celosías. Irreversible: por eso hay que escribir la frase de confirmación
    (la comprueba `UnmaskRequest`). Avisa a todos, por websocket o por push."""
    # FOR UPDATE: dos peticiones a la vez no pueden desenmascarar (ni avisar) dos veces.
    group = await db.scalar(
        select(Group)
        .where(Group.id == current.group.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert group is not None
    ensure_drawn(group)
    ensure_masked(group)

    group.unmasked_at = datetime.now(UTC)
    await db.commit()

    participant_ids = await db.scalars(
        select(Participant.id).where(Participant.group_id == group.id)
    )
    for participant_id in participant_ids.all():
        if manager.is_connected(participant_id):
            await manager.send(participant_id, {"type": "unmasked"})
        else:
            await notify(db, participant_id, unmask_push_payload(group.slug))
    return GroupPublic.model_validate(group)


def unmask_push_payload(slug: str) -> dict[str, str]:
    return {
        "title": "Se acabó el misterio",
        "body": "Ya se han quitado las celosías: entra a ver quién te regalaba",
        "url": f"/g/{slug}/resultados",
    }


def chain_order(gives_to: dict[uuid.UUID, uuid.UUID], order: list[uuid.UUID]) -> list[uuid.UUID]:
    """Quienes regalan, siguiendo la cadena: Ana -> Luis -> Marta -> ... Si el sorteo forma
    varios círculos, se empieza el siguiente por la primera persona (según `order`) que
    todavía no ha salido."""
    result: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for start in order:
        current = start
        while current not in seen:
            seen.add(current)
            result.append(current)
            current = gives_to[current]
    return result


@router.get("/results")
async def get_results(current: CurrentParticipantDep, db: DbSession) -> Results:
    """Quién regalaba a quién y quién acertó. Solo después de quitar las celosías."""
    if current.group.unmasked_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "las celosías siguen puestas")

    group_id = current.group.id
    people = {
        p.id: ParticipantRef(id=p.id, name=p.name)
        for p in await db.scalars(
            select(Participant)
            .where(Participant.group_id == group_id)
            .order_by(Participant.created_at, Participant.id)
        )
    }
    gives_to = {
        a.giver_id: a.receiver_id
        for a in await db.scalars(select(Assignment).where(Assignment.group_id == group_id))
    }
    guesses = {
        g.guesser_id: g.guessed_id
        for g in await db.scalars(select(Guess).where(Guess.group_id == group_id))
    }

    pairs = []
    for giver_id in chain_order(gives_to, list(people)):
        receiver_id = gives_to[giver_id]
        guess_id = guesses.get(receiver_id)
        pairs.append(
            ResultPair(
                giver=people[giver_id],
                receiver=people[receiver_id],
                receiver_guess=people[guess_id] if guess_id else None,
                guessed_right=guess_id == giver_id,
            )
        )
    return Results(pairs=pairs)
