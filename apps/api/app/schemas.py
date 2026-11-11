import uuid
from datetime import date, datetime
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
    demo: bool = False
    # Cuándo se quitaron las celosías; null mientras sigan puestas.
    unmasked_at: datetime | None = None


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


# --- chat ----------------------------------------------------------------------------------

# Tu papel en la conversación: "giver" es el chat con la persona a la que regalas;
# "receiver", el chat con quien te regala (que para ti es anónimo).
ChatRole = Literal["giver", "receiver"]


class MessageCreate(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class MessageOut(BaseModel):
    """Un mensaje tal y como lo ve cada lado. `mine` sustituye a cualquier id de remitente."""

    id: uuid.UUID
    mine: bool
    body: str
    created_at: datetime
    read_at: datetime | None


class Conversation(BaseModel):
    role: ChatRole
    messages: list[MessageOut]
    # Solo en el chat con quien te regala y solo cuando ya se han quitado las celosías.
    giver_name: str | None = None


class ChatSummary(BaseModel):
    """Mensajes sin leer en cada conversación, para las pestañas y la sala."""

    as_giver: int
    as_receiver: int


# --- apuestas y desenmascarado --------------------------------------------------------------

# Lo que hay que escribir para quitar las celosías. Sin tildes, para que nadie se atasque
# con el teclado del móvil.
UNMASK_PHRASE = "desenmascarar"


class GuessUpdate(BaseModel):
    guessed_id: uuid.UUID


class GuessStatus(BaseModel):
    """Tu apuesta y cuántas personas han apostado ya. Nunca quiénes ni por quién."""

    guessed: ParticipantRef | None
    guessers: int
    participants: int


class UnmaskRequest(BaseModel):
    confirm: str

    @field_validator("confirm")
    @classmethod
    def is_the_phrase(cls, value: str) -> str:
        if " ".join(value.split()).lower() != UNMASK_PHRASE:
            raise ValueError(f'escribe "{UNMASK_PHRASE}" para confirmar')
        return value


class ResultPair(BaseModel):
    """Una pareja del sorteo y la apuesta de quien recibía."""

    giver: ParticipantRef
    receiver: ParticipantRef
    receiver_guess: ParticipantRef | None
    guessed_right: bool


class Results(BaseModel):
    """La cadena completa, en el orden en que se regala: cada pareja empieza por quien
    recibía en la anterior (salvo cuando el sorteo forma varios círculos)."""

    pairs: list[ResultPair]


# --- push ----------------------------------------------------------------------------------


class PushKeys(BaseModel):
    p256dh: str = Field(max_length=200)
    auth: str = Field(max_length=100)


class PushSubscriptionIn(BaseModel):
    """Lo que devuelve `pushManager.subscribe()` en el navegador (PushSubscription.toJSON)."""

    endpoint: Annotated[str, StringConstraints(pattern=r"^https://", max_length=2000)]
    keys: PushKeys


class PushPublicKey(BaseModel):
    public_key: str


class DemoSwitch(BaseModel):
    name: ParticipantName
