# Caddy con la web ya compilada dentro. Se construye desde la raíz del repo.

# 1. Compilar la web (Vite) a estáticos.
FROM node:22-slim AS build
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
RUN pnpm install --frozen-lockfile --filter @psst/web...
COPY apps/web apps/web
RUN pnpm build:web

# 2. Servirla con Caddy, que además hace HTTPS y de proxy hacia la API.
FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /repo/apps/web/dist /srv
