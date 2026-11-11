"""PIN, tokens de sesión y slugs. Todo lo aleatorio sale de `secrets`, nunca de `random`."""

import asyncio
import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

# Un PIN de 4 cifras son 10 000 combinaciones: sin bloqueo se prueban todas en minutos.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

SESSION_MAX_AGE_SECONDS = 365 * 24 * 60 * 60

# Sin 0/o, 1/l/i: el enlace se puede dictar o copiar a mano sin confusiones.
SLUG_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
SLUG_LENGTH = 10

_pin_hasher = PasswordHasher()


async def hash_pin(pin: str) -> str:
    # argon2 es lento a propósito; se ejecuta en un hilo para no bloquear el event loop.
    return await asyncio.to_thread(_pin_hasher.hash, pin)


async def verify_pin(pin_hash: str, pin: str) -> bool:
    try:
        return await asyncio.to_thread(_pin_hasher.verify, pin_hash, pin)
    except VerificationError:
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # El token tiene 256 bits aleatorios: basta con SHA-256 (rápido y buscable),
    # no hace falta un hash lento como con el PIN.
    return hashlib.sha256(token.encode()).hexdigest()


def new_slug() -> str:
    return "".join(secrets.choice(SLUG_ALPHABET) for _ in range(SLUG_LENGTH))


SESSION_COOKIE_PREFIX = "psst_"


def session_cookie_name(slug: str) -> str:
    # Una cookie por grupo: se puede estar en varios grupos desde el mismo navegador.
    return f"{SESSION_COOKIE_PREFIX}{slug}"
