"""Conexiones websocket abiertas, en memoria.

Cada participante puede tener varias conexiones (móvil y portátil, dos pestañas…). Los
eventos se mandan a todas. Como está en memoria, solo vale con un worker de uvicorn: con
varios habría que pasar los eventos por Postgres LISTEN/NOTIFY o Redis.
"""

import uuid
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: defaultdict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    def connect(self, participant_id: uuid.UUID, websocket: WebSocket) -> None:
        self._connections[participant_id].add(websocket)

    def disconnect(self, participant_id: uuid.UUID, websocket: WebSocket) -> None:
        self._connections[participant_id].discard(websocket)
        if not self._connections[participant_id]:
            del self._connections[participant_id]

    async def send(self, participant_id: uuid.UUID, event: dict[str, Any]) -> None:
        """Manda el evento a todas las conexiones de esa persona; si no hay, no pasa nada."""
        for websocket in list(self._connections.get(participant_id, ())):
            try:
                await websocket.send_json(event)
            except Exception:  # noqa: BLE001 - una conexión rota no debe tumbar la petición
                self.disconnect(participant_id, websocket)


manager = ConnectionManager()
