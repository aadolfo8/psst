"""Sorteo y revelado."""

from random import SystemRandom

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from app.deps import CurrentAdminDep, CurrentParticipantDep, DbSession
from app.draw import DrawImpossible, draw_assignments
from app.models import Assignment, Exclusion, Group, Participant
from app.push import notify
from app.schemas import GroupPublic, Reveal, RevealedReceiver

router = APIRouter(prefix="/groups/{slug}", tags=["draw"])

MIN_PARTICIPANTS = 3

# Aleatoriedad del sistema operativo: nadie, tampoco el organizador, puede predecir el sorteo.
_rng = SystemRandom()


@router.post("/draw")
async def make_draw(current: CurrentAdminDep, db: DbSession) -> GroupPublic:
    """Hace el sorteo (o lo repite si nadie ha visto todavía su resultado).

    Todo ocurre en una transacción: o se guardan todas las asignaciones y el grupo pasa a
    "drawn", o no cambia nada. La respuesta no dice nada de quién regala a quién: el
    organizador también participa y solo ve lo suyo.
    """
    # FOR UPDATE: si llegan dos peticiones a la vez, la segunda espera a que acabe la primera
    # y ve el grupo ya sorteado.
    group = await db.scalar(
        select(Group)
        .where(Group.id == current.group.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert group is not None

    first_draw = group.status == "closed"
    if group.status == "open":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "cierra antes las inscripciones para hacer el sorteo"
        )
    if group.status == "drawn":
        someone = await db.scalar(
            select(Participant.name)
            .join(Assignment, Assignment.giver_id == Participant.id)
            .where(Assignment.group_id == group.id, Assignment.revealed_at.is_not(None))
            .limit(1)
        )
        if someone is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{someone} ya ha visto su resultado; el sorteo ya no se puede repetir",
            )
        await db.execute(delete(Assignment).where(Assignment.group_id == group.id))

    participants = {
        p.id: p.name
        for p in await db.scalars(select(Participant).where(Participant.group_id == group.id))
    }
    if len(participants) < MIN_PARTICIPANTS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"hacen falta al menos {MIN_PARTICIPANTS} personas para el sorteo",
        )
    exclusions = [
        frozenset((e.participant_a_id, e.participant_b_id))
        for e in await db.scalars(select(Exclusion).where(Exclusion.group_id == group.id))
    ]

    try:
        result = draw_assignments(participants, exclusions, _rng)
    except DrawImpossible as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None

    db.add_all(
        Assignment(group_id=group.id, giver_id=giver, receiver_id=receiver)
        for giver, receiver in result.items()
    )
    group.status = "drawn"
    await db.commit()

    # Aviso a todos menos al organizador, que es quien lo ha hecho. Solo la primera vez:
    # si se repite es porque nadie lo había mirado todavía, y ya tienen el aviso.
    if first_draw:
        for participant_id in participants:
            if participant_id != group.admin_participant_id:
                await notify(db, participant_id, draw_push_payload(group))
    return GroupPublic.model_validate(group)


def draw_push_payload(group: Group) -> dict[str, str]:
    return {
        "title": "Ya está el sorteo",
        "body": f"Entra en «{group.name}» y descubre a quién le regalas",
        "url": f"/g/{group.slug}/revelado",
    }


@router.post("/me/reveal")
async def reveal(current: CurrentParticipantDep, db: DbSession) -> Reveal:
    """A quién le regalas y su lista de deseos. La primera vez marca el resultado como visto.

    Es un POST porque tiene efecto: una vez visto, el organizador ya no puede repetir el sorteo.
    """
    assignment = await db.scalar(
        select(Assignment).where(Assignment.giver_id == current.participant.id)
    )
    if assignment is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "todavía no se ha hecho el sorteo")

    receiver = await db.get(Participant, assignment.receiver_id)
    assert receiver is not None
    if assignment.revealed_at is None:
        assignment.revealed_at = func.now()
        await db.commit()

    return Reveal(
        receiver=RevealedReceiver(id=receiver.id, name=receiver.name, wishlist=receiver.wishlist)
    )
