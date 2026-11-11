# Imagen de la API. Se construye con apps/api como contexto (lo hace el workflow de despliegue).

# 1. Instalar las dependencias exactas de uv.lock en /app/.venv.
FROM python:3.12.16-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Primero solo las dependencias: esta capa se reutiliza mientras no cambie uv.lock.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts

# 2. Imagen final: el mismo Python, la .venv y el código. Sin uv ni herramientas de build.
FROM python:3.12.16-slim

RUN useradd --create-home --uid 10001 psst
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

COPY --from=build /app /app

# Sin root dentro del contenedor.
USER psst

EXPOSE 8000
# Migraciones al arrancar y un solo worker: las conexiones websocket viven en memoria
# (ver app/realtime.py). --proxy-headers porque delante están los dos Caddy, y solo se
# llega a la API desde la red interna de la app.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
