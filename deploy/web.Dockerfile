# Caddy con la web ya compilada dentro. Se construye desde la raíz del repo.

# 1. Compilar la web (Vite) a estáticos.
FROM node:22.23.4-slim AS build
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
RUN pnpm install --frozen-lockfile --filter @psst/web...
COPY apps/web apps/web
RUN pnpm build:web

# 2. Servirla con Caddy, que además hace de proxy de /api hacia la API.
#    El HTTPS lo pone el Caddy compartido del VPS; este solo habla HTTP en el 8080.
FROM caddy:2.11.9-alpine
RUN addgroup -S psst && adduser -S -G psst psst \
    && chown -R psst:psst /data /config
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /repo/apps/web/dist /srv

# Sin root: por eso el puerto 8080 y no el 80.
USER psst
EXPOSE 8080
