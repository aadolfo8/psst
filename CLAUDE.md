# psst — instrucciones para Claude Code

## Cómo trabajar en este repo
- Háblame en español, directo y sin relleno.
- Antes de cada fase, propón un plan breve y espera mi confirmación.
- Commits pequeños, uno por fase como mínimo. No avances a la siguiente fase sin
  cumplir su resultado verificable.
- No metas dependencias sin justificarlas.
- Tengo que poder explicar todo el código en una entrevista: prefiere soluciones
  simples y legibles a soluciones ingeniosas.
- `apps/web/AGENTS.md` lo genera Next.js: esta versión de Next (16) puede diferir de
  lo que conoces. Consulta `apps/web/node_modules/next/dist/docs/` antes de usar APIs
  que no tengas claras.
- Trabajo en Windows. Los finales de línea están fijados a LF en `.gitattributes`.

## Comandos
- Base de datos: `pnpm db:up` (Postgres 16 en Docker en el puerto 5433 del host,
  usuario/clave/bd `psst`).
- API: en `apps/api`, `uv sync`, `uv run alembic upgrade head`,
  `uv run uvicorn app.main:app --reload`.
- Web: `pnpm install` y `pnpm dev:web`.
- Comprobaciones: `pnpm lint:web`, `pnpm typecheck:web`, `pnpm build:web`;
  en `apps/api`: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`.
- Nueva migración: `uv run alembic revision --autogenerate -m "..."`.

## Estado
- [x] Fase 0: esqueleto (monorepo, Postgres en Docker, lint, tests, CI).
- [x] Fase 1: grupos y unión con PIN.
- [ ] Fase 2 en adelante: ver el plan más abajo.

---

# Brief

## Objetivo
Web app (PWA) gratuita y sin cuentas para organizar un amigo invisible.
El organizador crea un grupo y comparte un enlace por WhatsApp. Cada participante
se une con su nombre y un PIN. Se hace el sorteo y cada uno ve a quién regala.
Lo diferencial: un chat anónimo entre quien regala y quien recibe, para acertar
con el regalo sin desvelar la identidad.

Fecha límite de la v1: usable con un grupo real antes del 1 de diciembre.

## Alcance v1
- Crear grupo: nombre, presupuesto y fecha del intercambio.
- Enlace de invitación + botón "Compartir por WhatsApp" (wa.me/?text=..., sin API).
- Unirse con nombre + PIN de 4 cifras. Sin email, sin teléfono, sin cuentas.
- Lista de deseos por participante (texto libre).
- El organizador (que también participa) define exclusiones entre parejas,
  cierra las inscripciones y lanza el sorteo.
- Pantalla de revelado: a quién te toca y su lista de deseos.
- Chat con dos conversaciones por persona:
  "Quien te regala" (anónimo) y "A quien regalas".
- Tiempo real con websockets: mensajes en vivo, "escribiendo…" y "leído".
- PWA instalable con notificaciones push al recibir un mensaje.
- Modo demo: grupo de ejemplo ya sorteado en el que se puede cambiar
  entre dos participantes para ver el anonimato desde los dos lados.

## Fuera de alcance (v1)
- Que el organizador meta los nombres y reparta enlaces individuales.
- "Modo disfraz" con IA (reescribir mensajes en tono neutro). Va en la fase 2
  del producto, después de la v1.
- App nativa. Opcional después de Navidad, reutilizando la API.
- Cuentas, email, recuperación por SMS, varios idiomas.
- Gestionar bajas después del sorteo (en la v1, el organizador repite el sorteo
  solo si nadie ha visto todavía su resultado).

## Stack y decisiones
- Monorepo: apps/web (Next.js App Router, pnpm) y apps/api (FastAPI, Python 3.12,
  gestionado con uv).
- Backend: FastAPI + SQLAlchemy 2.0 en modo async con asyncpg, migraciones con
  Alembic y esquemas con Pydantic v2. Configuración con pydantic-settings
  (variables con prefijo `PSST_`).
- Base de datos: Postgres. Motivo: los datos son relacionales (grupos,
  participantes, exclusiones, asignaciones) y el sorteo necesita restricciones
  unique y transacciones. El chat no justifica una base de datos documental:
  son cientos de mensajes por grupo.
- Estilos: CSS Modules + variables CSS en `globals.css` (sin Tailwind).
  Tipografía Archivo con `next/font/google` y eje de ancho.
- Tipos compartidos: se genera el cliente TypeScript del frontend a partir del
  OpenAPI de FastAPI (openapi-typescript), en lugar de mantener tipos a mano.
- Websockets nativos de FastAPI con un ConnectionManager propio en memoria:
  una sala por pareja (assignment). Se ejecuta uvicorn con un solo worker;
  documentar en el README que con varios workers habría que usar LISTEN/NOTIFY
  de Postgres o Redis pub/sub.
- Notificaciones push: Web Push con claves VAPID y la librería pywebpush,
  más un service worker en Next. En iOS solo funciona si la web está instalada
  en la pantalla de inicio, así que hay que mostrar una ayuda para instalarla.
- Sesión sin cuentas: al unirse se crea un token de sesión guardado en una cookie
  httpOnly asociada al grupo. Con nombre + PIN se recupera la sesión en otro
  dispositivo.
- El PIN se guarda con hash (argon2-cffi). Se bloquea tras 5 intentos fallidos
  durante 15 minutos, porque 4 cifras se pueden probar todas por fuerza bruta.
- Anonimato: la API nunca envía al receptor el id ni el nombre de quien le regala,
  ni por REST ni por websocket. Debe haber tests que lo comprueben.
- Despliegue: Docker Compose en el VPS (web, api, postgres) con Caddy delante
  para HTTPS automático, que es obligatorio para el service worker y las push.
  Caddy también hace de proxy para los websockets.

## Algoritmo de sorteo
- Asignación aleatoria en la que nadie se toca a sí mismo y se respetan
  las exclusiones (simétricas).
- Backtracking aleatorizado; con grupos de hasta 50 personas es suficiente.
- Si no hay ninguna solución posible, devolver un error claro
  ("Ana no puede regalar a nadie con estas exclusiones").
- Tests basados en propiedades con Hypothesis: biyección, sin autoasignaciones,
  exclusiones respetadas y error correcto cuando es imposible.
- El sorteo se guarda en una sola transacción.

## Modelo de datos
- groups: id, slug, name, budget, exchange_date, status (open | closed | drawn),
  admin_participant_id, created_at
- participants: id, group_id, name, pin_hash, failed_attempts, locked_until,
  wishlist, created_at — unique(group_id, lower(name))
- sessions: id, participant_id, token_hash, created_at, last_seen_at
- exclusions: group_id, participant_a_id, participant_b_id
- assignments: id, group_id, giver_id, receiver_id, revealed_at
  — unique(group_id, giver_id), unique(group_id, receiver_id)
- messages: id, assignment_id, sender_role (giver | receiver), body,
  created_at, read_at
- push_subscriptions: id, participant_id, endpoint, p256dh, auth, created_at

## Pantallas y flujos
1. Inicio: titular con una barra que tapa un nombre, formulario para crear grupo
   y enlace a "Probar la demo".
2. Compartir: enlace del grupo y botón de WhatsApp con el mensaje ya redactado.
3. Unirse: nombre + PIN, con la explicación de para qué sirve el PIN.
4. Sala de espera: apuntados, lista de deseos y, si eres el organizador,
   exclusiones y "Hacer el sorteo".
5. Revelado: el nombre aparece tapado por una barra rosa que se retira.
   Debajo, la lista de deseos y "Preguntarle algo en secreto".
6. Chat: dos pestañas, "escribiendo…", "leído" y no leídos. Quien te escribe
   aparece como una barra, nunca con nombre ni iniciales.
7. Activar avisos: se ofrece tras el primer mensaje recibido, con el paso a paso
   para iPhone.

## Dirección visual
- Concepto: lo secreto va tapado con una barra, como en un documento censurado,
  y revelar es quitarla. Las barras son el único elemento llamativo.
- Colores (ya definidos como variables en `apps/web/src/app/globals.css`):
  fondo vino #2A0A10, superficies #3A1219, líneas #5A2530, texto #FBEDEF,
  texto secundario #D9A9B1, rojo #E0283C solo para acciones y para tus mensajes,
  y rosa #F7C6CF para las barras y la pestaña activa.
- Tipografía: Archivo. Titulares en peso 800 y ancho 112 %, con interlineado
  ajustado; interfaz en ancho normal, entre 15 y 17 px.
- Formas: botones en forma de píldora; campos con 10 px de radio; bloques
  con 18 px. Bordes finos (1–1,5 px). Sin sombras ni degradados.
- Texto: frases en minúscula, sin etiquetas en mayúsculas, sin "·" entre datos
  y sin flechas añadidas al texto de los botones.
- Movimiento: una sola animación con intención, la barra que se retira en el
  revelado. Respetar prefers-reduced-motion.
- Referencia: bocetos de las 7 pantallas en el lienzo de diseño "psst — bocetos"
  (claude.ai).

## Plan por fases (un commit por fase, cada fase verificable)
0. Esqueleto: monorepo, Postgres en Docker, ruff + pytest en la API, lint en web
   y CI en GitHub Actions. HECHA.
1. Grupos y unión: modelos, migración inicial, crear grupo, unirse con PIN,
   sesión y bloqueo por intentos.
   Verificable: tests con httpx de crear, unirse, recuperar sesión y bloqueo.
   Commit: "feat: groups and PIN join". HECHA.
2. Sala de espera: apuntados, lista de deseos y exclusiones, con el cliente
   generado desde OpenAPI.
   Verificable: el flujo completo funciona en el navegador con dos sesiones.
   Commit: "feat: lobby, wishlist and exclusions"
3. Sorteo y revelado: algoritmo con tests de Hypothesis y pantalla de revelado
   con la animación de la barra.
   Verificable: tests verdes y caso imposible gestionado.
   Commit: "feat: constrained draw and reveal"
4. Chat asíncrono: endpoints REST, persistencia y no leídos, más tests de que
   no se filtra la identidad.
   Verificable: el receptor nunca recibe el giver_id.
   Commit: "feat: anonymous async chat"
5. Tiempo real: websockets, ConnectionManager, "escribiendo…" y "leído".
   Verificable: dos navegadores ven los cambios en vivo.
   Commit: "feat: realtime chat via websockets"
6. PWA y push: manifest, service worker, VAPID, suscripciones y ayuda para iOS.
   Verificable: llega una push en Android y en un iPhone con la web instalada.
   Commit: "feat: PWA and web push"
7. Pulido visual y modo demo.
   Verificable: alguien ajeno lo entiende y lo prueba en menos de un minuto.
   Commit: "feat: visual polish and demo mode"
8. Despliegue y README.
   Verificable: funciona por HTTPS en el subdominio y el README está completo.
   Commit: "docs: README and deploy"

## Criterios de terminado
- Desplegado en el VPS con HTTPS y la demo accesible desde la página de inicio.
- Instalable como PWA y con push probadas en Android y en iOS.
- Tests del sorteo y del anonimato pasando en la CI.
- README con: GIF del revelado y del chat, por qué existe el proyecto
  (qué aporta frente a las webs que ya existen), decisiones técnicas
  (FastAPI + Postgres y por qué no Mongo, PWA en vez de app nativa,
  PIN en vez de teléfono, websockets más push, límites honestos del anonimato)
  y cómo se usó la IA en el desarrollo.
- Usado por al menos un grupo real antes de Navidad, con notas de lo que aprendí.
