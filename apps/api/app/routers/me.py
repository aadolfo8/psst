from fastapi import APIRouter, Request

from app.deps import DbSession, find_session
from app.schemas import GroupPublic
from app.security import SESSION_COOKIE_PREFIX

router = APIRouter(prefix="/me", tags=["me"])

# Tope de cookies que se miran: cada una es una consulta, y nadie está en tantos grupos.
MAX_GROUPS = 20


@router.get("/groups")
async def my_groups(request: Request, db: DbSession) -> list[GroupPublic]:
    """Los grupos en los que este navegador tiene sesión, de más nuevo a más antiguo.

    Sirve para que la app instalada, que arranca en `/`, sepa a qué grupo llevarte: la cookie
    es httpOnly y desde JavaScript no se puede leer. Solo se mira lo que manda el propio
    navegador, así que nunca devuelve grupos de otra persona."""
    groups = []
    for name, token in request.cookies.items():
        if not name.startswith(SESSION_COOKIE_PREFIX) or len(groups) >= MAX_GROUPS:
            continue
        slug = name.removeprefix(SESSION_COOKIE_PREFIX)
        current = await find_session(db, slug, token)
        if current is not None:
            groups.append(current.group)

    groups.sort(key=lambda group: group.created_at, reverse=True)
    return [GroupPublic.model_validate(group) for group in groups]
