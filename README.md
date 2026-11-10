# psst

El amigo invisible por enlace. Cada persona ve solo a quién le toca regalar y puede
preguntarle cosas en un chat anónimo, sin que sepa quién pregunta.

> En construcción. Este README se completará en la fase 8 con capturas, el porqué del
> proyecto y las decisiones técnicas.

## Estructura

```
apps/
  web/   Vite + React + TypeScript + React Router — PWA
  api/   FastAPI + SQLAlchemy async + Alembic
```

## Desarrollo local

Requisitos: Node 22 con pnpm, [uv](https://docs.astral.sh/uv/) y Docker.

```bash
# Base de datos
pnpm db:up

# API (http://localhost:8000, docs en /docs)
cd apps/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Web (http://localhost:3000)
pnpm install
pnpm dev:web
```

## Comprobaciones

```bash
pnpm lint:web && pnpm typecheck:web && pnpm build:web
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run pytest
```
