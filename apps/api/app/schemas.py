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
    group: GroupPublic
