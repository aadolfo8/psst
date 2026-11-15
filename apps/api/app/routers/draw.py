"""Sorteo y revelado."""

import uuid
from random import SystemRandom

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentAdminDep, CurrentParticipantDep, DbSession
from app.draw import (
    NO_LATE_ROOM,
    DrawImpossible,
    close_gap,
    draw_assignments,
    has_late_room,
    insert_late,
)
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


@router.post("/participants/{participant_id}/withdraw")
async def withdraw(
    participant_id: uuid.UUID, current: CurrentAdminDep, db: DbSession
) -> GroupPublic:
    """Alguien no puede ir después del sorteo: se le quita y se recoloca lo mínimo.

    Ver `close_gap`: normalmente solo cambia a quién regala quien le regalaba a esa persona.
    Las conversaciones de las parejas que cambian se pierden (se borran en cascada) y quien
    tiene destinatario nuevo debe volver a abrir su celosía; se le avisa por push.
    """
    group = await db.scalar(
        select(Group)
        .where(Group.id == current.group.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert group is not None
    if group.status != "drawn":
        raise HTTPException(status.HTTP_409_CONFLICT, "todavía no se ha hecho el sorteo")
    if group.unmasked_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "las celosías ya están quitadas")
    if participant_id == group.admin_participant_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "no puedes quitarte a ti del grupo")

    gives_to = {
        a.giver_id: a.receiver_id
        for a in await db.scalars(select(Assignment).where(Assignment.group_id == group.id))
    }
    if participant_id not in gives_to:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "esa persona no está en el grupo")
    exclusions = [
        frozenset((e.participant_a_id, e.participant_b_id))
        for e in await db.scalars(select(Exclusion).where(Exclusion.group_id == group.id))
    ]

    try:
        new = close_gap(gives_to, participant_id, exclusions, _rng)
    except DrawImpossible as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None

    # Quienes regalan a alguien distinto que antes. Sus asignaciones viejas se borran con
    # DELETE directos (antes de insertar, por las restricciones unique) y la persona que se
    # va, también: la base de datos borra en cascada lo suyo, chats incluidos.
    changed = [giver for giver, receiver in new.items() if gives_to[giver] != receiver]
    await db.execute(
        delete(Assignment).where(Assignment.group_id == group.id, Assignment.giver_id.in_(changed))
    )
    await db.execute(delete(Participant).where(Participant.id == participant_id))
    db.add_all(
        Assignment(group_id=group.id, giver_id=giver, receiver_id=new[giver]) for giver in changed
    )
    await db.commit()

    for giver in changed:
        await notify(db, giver, reassigned_push_payload(group))
    return GroupPublic.model_validate(group)


def reassigned_push_payload(group: Group) -> dict[str, str]:
    return {
        "title": "Cambio en el sorteo",
        "body": f"Alguien de «{group.name}» no puede ir: te toca regalar a otra persona",
        "url": f"/g/{group.slug}/revelado",
    }


async def current_draw(
    db: AsyncSession, group: Group
) -> tuple[dict[uuid.UUID, uuid.UUID], set[uuid.UUID]]:
    """El reparto actual ({quien regala: a quien}) y quiénes no han mirado todavía el suyo."""
    assignments = list(await db.scalars(select(Assignment).where(Assignment.group_id == group.id)))
    gives_to = {a.giver_id: a.receiver_id for a in assignments}
    not_revealed = {a.giver_id for a in assignments if a.revealed_at is None}
    return gives_to, not_revealed


async def lock_drawn_group(db: AsyncSession, group_id: uuid.UUID) -> Group:
    """Relee el grupo bloqueándolo. Las altas tardías, las bajas y los revelados (que lo
    bloquean en modo compartido) se hacen así de una en una y no se pisan."""
    group = await db.scalar(
        select(Group)
        .where(Group.id == group_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert group is not None
    if group.status != "drawn":
        raise HTTPException(status.HTTP_409_CONFLICT, "todavía no se ha hecho el sorteo")
    if group.unmasked_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "las celosías ya están quitadas")
    return group


@router.post("/late-join")
async def open_late_join(current: CurrentAdminDep, db: DbSession) -> GroupPublic:
    """Deja entrar a gente que llega después del sorteo.

    Mientras esté abierto, quien tenga el enlace puede unirse y entra en el sorteo al momento
    (ver `insert_late`). Puede entrar más de una persona, mientras quede hueco: cada alta lo
    vuelve a comprobar. Solo se abre si ahora mismo lo hay.
    """
    group = await lock_drawn_group(db, current.group.id)
    gives_to, not_revealed = await current_draw(db, group)
    if not has_late_room(gives_to, not_revealed):
        raise HTTPException(status.HTTP_409_CONFLICT, NO_LATE_ROOM)
    group.late_join_open = True
    await db.commit()
    return GroupPublic.model_validate(group)


@router.delete("/late-join")
async def close_late_join(current: CurrentAdminDep, db: DbSession) -> GroupPublic:
    current.group.late_join_open = False
    await db.commit()
    return GroupPublic.model_validate(current.group)


async def place_late_joiner(db: AsyncSession, group: Group, newcomer: uuid.UUID) -> None:
    """Mete en el sorteo a quien acaba de unirse. Lanza DrawImpossible si ya no hay hueco.
    El grupo tiene que venir bloqueado (`lock_drawn_group`).

    Pepe -> Xavi pasa a ser Pepe -> recién llegado -> Xavi. La fila de Pepe -> Xavi no se
    borra: se le cambia quién regala. Así los mensajes que Xavi ya había escrito a "quien te
    regala" (y que Pepe no ha podido leer, porque no había mirado) le llegan a quien de verdad
    le regala ahora.
    """
    gives_to, not_revealed = await current_draw(db, group)
    new = insert_late(gives_to, newcomer, not_revealed, _rng)
    giver = next(g for g in gives_to if new[g] != gives_to[g])  # Pepe

    # Primero el UPDATE y luego el INSERT, por las restricciones unique de giver y receiver.
    await db.execute(
        update(Assignment)
        .where(Assignment.group_id == group.id, Assignment.giver_id == giver)
        .values(giver_id=newcomer)
    )
    db.add(Assignment(group_id=group.id, giver_id=giver, receiver_id=newcomer))


@router.post("/me/reveal")
async def reveal(current: CurrentParticipantDep, db: DbSession) -> Reveal:
    """A quién le regalas y su lista de deseos. La primera vez marca el resultado como visto.

    Es un POST porque tiene efecto: una vez visto, el organizador ya no puede repetir el sorteo.
    """
    # Bloqueo compartido del grupo: varios pueden mirar a la vez, pero nadie mientras alguien
    # entra tarde en el sorteo, que justo elige entre quienes no han mirado.
    await db.execute(
        select(Group.id).where(Group.id == current.group.id).with_for_update(read=True)
    )
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
