import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (CheckConstraint("status IN ('open', 'closed', 'drawn')", name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # El slug va en el enlace de invitación: quien lo tiene puede unirse, así que es aleatorio.
    slug: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    budget: Mapped[int | None]
    exchange_date: Mapped[date | None]
    status: Mapped[str] = mapped_column(String(10), default="open", server_default="open")
    # use_alter: groups y participants se referencian entre sí, así que esta FK
    # se crea después de las dos tablas.
    admin_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participants.id", use_alter=True, ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(40))
    pin_hash: Mapped[str] = mapped_column(String(200))
    failed_attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wishlist: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# "Ana" y "ana" son la misma persona dentro de un grupo.
Index(
    "uq_participants_group_id_lower_name",
    Participant.group_id,
    func.lower(Participant.name),
    unique=True,
)


class ParticipantSession(Base):
    """Sesión de un participante en un dispositivo. Solo se guarda el hash del token."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Exclusion(Base):
    """Dos participantes que no pueden tocarse entre sí (en ningún sentido).

    La pareja se guarda ordenada (a < b), así "Ana-Luis" y "Luis-Ana" son la misma fila
    y la restricción unique impide duplicarla.
    """

    __tablename__ = "exclusions"
    __table_args__ = (
        CheckConstraint("participant_a_id < participant_b_id", name="ordered_pair"),
        UniqueConstraint("group_id", "participant_a_id", "participant_b_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    participant_a_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE")
    )
    participant_b_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
