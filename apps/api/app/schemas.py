import uuid
from datetime import date
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


def _normalize_spaces(value: object) -> object:
    """Quita espacios al principio y al final y colapsa los repetidos: " Ana   M " -> "Ana M"."""
    if isinstance(value, str):
        return " ".join(value.split())
    return value


ParticipantName = Annotated[
    str, BeforeValidator(_normalize_spaces), StringConstraints(min_length=1, max_length=40)
]
GroupName = Annotated[
    str, BeforeValidator(_normalize_spaces), StringConstraints(min_length=1, max_length=80)
]
# [0-9] y no \d: \d también acepta cifras de otros alfabetos, como "١٢٣٤".
Pin = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}$")]


class GroupCreate(BaseModel):
    name: GroupName
    budget: int | None = Field(default=None, ge=1, le=1000, description="En euros")
    exchange_date: date | None = None
    admin_name: ParticipantName
    pin: Pin

    @field_validator("exchange_date")
    @classmethod
    def exchange_date_not_in_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("la fecha del intercambio no puede ser pasada")
        return value


class ParticipantCredentials(BaseModel):
    """Nombre + PIN: sirve tanto para unirse como para recuperar la sesión."""

    name: ParticipantName
    pin: Pin


class GroupPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    budget: int | None
    exchange_date: date | None
    status: Literal["open", "closed", "drawn"]


class Me(BaseModel):
    id: uuid.UUID
    name: str
    is_admin: bool
    wishlist: str
    # Si ya has visto a quién le regalas (para no repetir la animación del revelado).
    revealed: bool
    group: GroupPublic


class ParticipantPublic(BaseModel):
    """Lo que ven los demás de un participante en la sala de espera: sin lista de deseos."""

    id: uuid.UUID
    name: str
    is_admin: bool
    has_revealed: bool


class WishlistUpdate(BaseModel):
    wishlist: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class GroupStatusUpdate(BaseModel):
    # "drawn" no se puede poner a mano: solo lo pone el sorteo (fase 3).
    status: Literal["open", "closed"]


class ExclusionCreate(BaseModel):
    participant_a_id: uuid.UUID
    participant_b_id: uuid.UUID

    @model_validator(mode="after")
    def different_participants(self) -> "ExclusionCreate":
        if self.participant_a_id == self.participant_b_id:
            raise ValueError("una exclusión necesita dos personas distintas")
        return self


class ParticipantRef(BaseModel):
    id: uuid.UUID
    name: str


class ExclusionOut(BaseModel):
    id: uuid.UUID
    participant_a: ParticipantRef
    participant_b: ParticipantRef


class RevealedReceiver(BaseModel):
    id: uuid.UUID
    name: str
    wishlist: str


class Reveal(BaseModel):
    """Lo que ve quien regala. Nunca incluye nada de quien le regala a él."""

    receiver: RevealedReceiver
