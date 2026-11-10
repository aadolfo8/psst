"""Notificaciones push (Web Push con VAPID).

Las claves VAPID identifican a este servidor ante los servicios de push de los navegadores.
Se generan una vez con `uv run python -m scripts.gen_vapid` y van en PSST_VAPID_PRIVATE_KEY y
PSST_VAPID_PUBLIC_KEY. Sin ellas, la app funciona igual pero sin avisos.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import PushSubscription

log = logging.getLogger(__name__)

# Códigos con los que el servicio de push dice que esa suscripción ya no existe.
GONE_STATUSES = {404, 410}


def push_enabled() -> bool:
    settings = get_settings()
    return bool(settings.vapid_private_key and settings.vapid_public_key)


async def send_push(subscription: PushSubscription, payload: dict[str, Any]) -> bool:
    """Manda la notificación a un dispositivo. Devuelve False si la suscripción ya no vale
    (y hay que borrarla). pywebpush es síncrono (usa requests): se ejecuta en un hilo."""
    settings = get_settings()
    try:
        await asyncio.to_thread(
            webpush,
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=60 * 60 * 24,  # si el móvil está apagado, el servicio la guarda un día
        )
    except WebPushException as error:
        status = error.response.status_code if error.response is not None else None
        if status in GONE_STATUSES:
            return False
        log.warning("push fallida (%s): %s", status, error)
    return True


async def notify(db: AsyncSession, participant_id: uuid.UUID, payload: dict[str, Any]) -> None:
    """Manda la notificación a todos los dispositivos de una persona y olvida los que ya no
    existen. Si las push no están configuradas, no hace nada."""
    if not push_enabled():
        return
    subscriptions = await db.scalars(
        select(PushSubscription).where(PushSubscription.participant_id == participant_id)
    )
    for subscription in subscriptions:
        if not await send_push(subscription, payload):
            await db.delete(subscription)
    await db.commit()
