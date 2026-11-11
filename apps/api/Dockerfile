# Imagen de la API. Se construye desde la raíz del repo con deploy/docker-compose.yml.
FROM python:3.12-slim

# uv instala las dependencias exactas de uv.lock, igual que en desarrollo.
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Primero solo las dependencias: esta capa se reutiliza mientras no cambie uv.lock.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# Sin root dentro del contenedor.
RUN useradd --create-home psst
USER psst

EXPOSE 8000
# Migraciones al arrancar y un solo worker: las conexiones websocket viven en memoria
# (ver app/realtime.py). --proxy-headers porque delante está Caddy.
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
