"""Modo demo: un grupo de ejemplo ya sorteado para probar la app sin montar nada.

Cada visita crea su propio grupo (así dos personas probando a la vez no se pisan) y se entra
como Lucía. En los grupos demo se puede cambiar de persona sin PIN para ver el chat desde los
dos lados: Lucía sabe que le regala a Mario; Mario solo ve a "su amigo invisible".
Los grupos demo se borran pasado un día.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, func, select

from app.deps import DbSession
from app.models import Assignment, Group, Guess, Message, Participant
from app.routers.groups import build_me, open_session, set_session_cookie
from app.schemas import DemoSwitch, Me
from app.security import hash_pin, new_slug

router = APIRouter(tags=["demo"])

DEMO_MAX_AGE = timedelta(days=1)

# Nombre, lista de deseos. El orden es el del sorteo: cada uno regala al siguiente.
PEOPLE = [
    ("Lucía", "Un libro que me haga reír. Calcetines bonitos. Nada de velas, ya tengo mil."),
    ("Mario", "Café de especialidad. Talla M. Me gustan los puzles difíciles."),
    ("Carmen", "Plantas que no se mueran fácil. Té verde."),
    ("Pablo", "Algo para el gimnasio o un vinilo de los 80."),
]

# Conversación entre Lucía (regala) y Mario (recibe), en orden.
CONVERSATION = [
    ("giver", "psst. ¿qué talla de jersey usas?"),
    ("receiver", "una m. ¿quién eres? 👀"),
    ("giver", "eso no se pregunta. ¿más de té o de café?"),
    ("receiver", "café, siempre"),
]

# Apuestas ya hechas (quien apuesta, por quién). Mario acierta; Carmen y Pablo fallan; Lucía
# no ha apostado para que quien prueba la demo lo haga.
GUESSES = [("Mario", "Lucía"), ("Carmen", "Pablo"), ("Pablo", "Lucía")]


@router.post("/demo", status_code=status.HTTP_201_CREATED)
async def create_demo(response: Response, db: DbSession) -> Me:
    """Crea el grupo de ejemplo y abre sesión como Lucía."""
    await db.execute(
        delete(Group).where(
            Group.demo.is_(True), Group.created_at < datetime.now(UTC) - DEMO_MAX_AGE
        )
    )

    group = Group(
        slug=new_slug(),
        name="Cena de Navidad",
        budget=25,
        exchange_date=datetime.now(UTC).date().replace(month=12, day=24),
        status="drawn",
        demo=True,
    )
    db.add(group)
    await db.flush()

    # Un PIN cualquiera: en la demo no hace falta para entrar.
    pin_hash = await hash_pin("0000")
    now = datetime.now(UTC)
    people = [
        Participant(
            group_id=group.id,
            name=name,
            pin_hash=pin_hash,
            wishlist=wishlist,
            # Un segundo de diferencia para que la sala los liste en este orden.
            created_at=now + timedelta(seconds=i),
        )
        for i, (name, wishlist) in enumerate(PEOPLE)
    ]
    db.add_all(people)
    await db.flush()
    group.admin_participant_id = people[0].id

    # Sorteo en círculo, todos con su resultado ya visto para que el chat esté disponible.
    assignments = [
        Assignment(
            group_id=group.id,
            giver_id=giver.id,
            receiver_id=receiver.id,
            revealed_at=func.now(),
        )
        for giver, receiver in zip(people, people[1:] + people[:1], strict=True)
    ]
    db.add_all(assignments)
    await db.flush()

    db.add_all(
        Message(
            assignment_id=assignments[0].id,
            sender_role=role,
            body=body,
            # Dentro de una transacción now() es el mismo instante: se escalonan a mano.
            created_at=now + timedelta(seconds=i),
        )
        for i, (role, body) in enumerate(CONVERSATION)
    )

    by_name = {p.name: p for p in people}
    db.add_all(
        Guess(group_id=group.id, guesser_id=by_name[guesser].id, guessed_id=by_name[guessed].id)
        for guesser, guessed in GUESSES
    )

    token = open_session(db, people[0])
    await db.commit()
    set_session_cookie(response, group.slug, token)
    return await build_me(db, people[0], group)


@router.post("/groups/{slug}/demo/switch")
async def switch_person(slug: str, data: DemoSwitch, response: Response, db: DbSession) -> Me:
    """Entra como otra persona del grupo demo, sin PIN. Solo en grupos demo."""
    group = await db.scalar(select(Group).where(Group.slug == slug, Group.demo.is_(True)))
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "esto solo funciona en la demo")

    participant = await db.scalar(
        select(Participant).where(
            Participant.group_id == group.id,
            func.lower(Participant.name) == func.lower(data.name),
        )
    )
    if participant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "esa persona no está en el grupo")

    token = open_session(db, participant)
    await db.commit()
    set_session_cookie(response, slug, token)
    return await build_me(db, participant, group)
