from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.routers import chat, demo, draw, groups, lobby, push, ws

app = FastAPI(title="psst API", version="0.1.0")
app.include_router(groups.router)
app.include_router(lobby.router)
app.include_router(draw.router)
app.include_router(chat.router)
app.include_router(ws.router)
app.include_router(push.router)
app.include_router(demo.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
