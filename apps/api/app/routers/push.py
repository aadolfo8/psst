"""Suscripciones push de cada dispositivo."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.deps import CurrentParticipantDep, DbSession
from app.models import PushSubscription
from app.push import push_enabled
from app.schemas import PushPublicKey, PushSubscriptionIn

router = APIRouter(tags=["push"])


@router.get("/push/public-key")
async def public_key() -> PushPublicKey:
    """La clave pública VAPID, que el navegador necesita para suscribirse."""
    if not push_enabled():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "los avisos no están configurados")
    return PushPublicKey(public_key=get_settings().vapid_public_key)


@router.put("/groups/{slug}/me/push", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe(
    data: PushSubscriptionIn, current: CurrentParticipantDep, db: DbSession
) -> Response:
    """Guarda la suscripción de este dispositivo. Es un PUT: repetirla no duplica nada."""
    db.add(
        PushSubscription(
            participant_id=current.participant.id,
            endpoint=data.endpoint,
            p256dh=data.keys.p256dh,
            auth=data.keys.auth,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()  # ya estaba: el endpoint es único
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/groups/{slug}/me/push", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    data: PushSubscriptionIn, current: CurrentParticipantDep, db: DbSession
) -> Response:
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.participant_id == current.participant.id,
            PushSubscription.endpoint == data.endpoint,
        )
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
