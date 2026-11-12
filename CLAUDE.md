# psst — instrucciones para Claude Code

## Cómo trabajar en este repo
- Háblame en español, directo y sin relleno.
- Antes de cada fase, propón un plan breve y espera mi confirmación.
- Commits pequeños, uno por fase como mínimo. No avances a la siguiente fase sin
  cumplir su resultado verificable.
- No metas dependencias sin justificarlas.
- Tengo que poder explicar todo el código en una entrevista: prefiere soluciones
  simples y legibles a soluciones ingeniosas.
- React Router (v8) y Vite (v8) pueden diferir de lo que conoces: consulta
  `apps/web/node_modules/react-router/docs/` antes de usar APIs que no tengas claras.
- Trabajo en Windows. Los finales de línea están fijados a LF en `.gitattributes`.

## Comandos
- Base de datos: `pnpm db:up` (Postgres 16 en Docker en el puerto 5433 del host,
  usuario/clave/bd `psst`).
- API: en `apps/api`, `uv sync`, `uv run alembic upgrade head`,
  `uv run uvicorn app.main:app --reload`.
- Web: `pnpm install` y `pnpm dev:web`.
- Comprobaciones: `pnpm lint:web`, `pnpm typecheck:web`, `pnpm test:web`, `pnpm build:web`;
  en `apps/api`: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`.
- Nueva migración: `uv run alembic revision --autogenerate -m "..."`.

## Estado
- [x] Fase 0: esqueleto (monorepo, Postgres en Docker, lint, tests, CI).
- [x] Fase 1: grupos y unión con PIN.
- [x] Fase 2: sala de espera, lista de deseos y exclusiones.
- [x] Fase 3: sorteo con exclusiones y revelado.
- [x] Fase 4: chat asíncrono (REST) con tests de anonimato.
- [x] Fase 5: tiempo real con websockets (mensajes, "escribiendo…" y "leído").
- [x] Fase 6: PWA y push (código y tests; falta probar la push en Android e iPhone
  con HTTPS).
- [x] Fase 7: modo demo y pulido (falta que alguien ajeno lo pruebe).
- [x] Fase 8: README y ficheros de despliegue en `deploy/` (probados en local con
  Docker). Falta desplegar en el VPS, grabar los GIFs y probar las push en móvil.

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

## Stack y decisiones
- Monorepo: apps/web (Vite + React + TypeScript, pnpm) y apps/api (FastAPI,
  Python 3.12, gestionado con uv).
- Frontend: SPA con React Router en modo data (`createBrowserRouter`). Los datos se
  piden desde el cliente a `/api`, que en desarrollo reenvía el proxy de Vite y en
  producción Caddy: mismo origen, sin CORS, y la cookie de sesión es de la web.
  Motivo frente a Next.js: la web es una SPA detrás de una API propia; no necesita
  renderizado en servidor y en producción se sirve como estáticos, sin Node.
- Backend: FastAPI + SQLAlchemy 2.0 en modo async con asyncpg, migraciones con
  Alembic y esquemas con Pydantic v2. Configuración con pydantic-settings
  (variables con prefijo `PSST_`).
- Base de datos: Postgres. Motivo: los datos son relacionales (grupos,
  participantes, exclusiones, asignaciones) y el sorteo necesita restricciones
  unique y transacciones. El chat no justifica una base de datos documental:
  son cientos de mensajes por grupo.
- Estilos: CSS Modules + variables CSS en `globals.css` (sin Tailwind).
  Tipografías Reem Kufi (titulares) y Onest (interfaz) autoalojadas con
  `@fontsource-variable/reem-kufi` y `@fontsource-variable/onest`, para que
  funcionen sin conexión en la PWA y no dependan de Google Fonts.
- Tipos compartidos: se genera el cliente TypeScript del frontend a partir del
  OpenAPI de FastAPI (openapi-typescript), en lugar de mantener tipos a mano.
- Websockets nativos de FastAPI con un ConnectionManager propio en memoria:
  una conexión por participante (`/groups/{slug}/ws`, misma cookie de sesión y
  comprobación del Origin) por la que llegan los eventos de sus dos conversaciones.
  Enviar y marcar leído van por REST; el socket solo empuja (mensaje, leído,
  escribiendo…). Se ejecuta uvicorn con un solo worker;
  documentar en el README que con varios workers habría que usar LISTEN/NOTIFY
  de Postgres o Redis pub/sub.
- Notificaciones push: Web Push con claves VAPID (se generan con
  `uv run python -m scripts.gen_vapid` y van en las variables `PSST_VAPID_*`) y la
  librería pywebpush. Solo se envía si la otra persona no tiene el websocket abierto;
  el aviso lleva el texto del mensaje pero nunca nombres. Suscripciones por dispositivo
  en `push_subscriptions`; las caducadas (404/410) se borran al fallar. Service worker
  propio (`apps/web/src/sw.ts`) generado con vite-plugin-pwa (estrategia injectManifest,
  para poder escribir el manejador de `push`; precaché con workbox). En iOS solo funciona
  si la web está instalada en la pantalla de inicio, así que el chat enseña cómo hacerlo.
- Sesión sin cuentas: al unirse se crea un token de sesión guardado en una cookie
  httpOnly asociada al grupo. Con nombre + PIN se recupera la sesión en otro
  dispositivo.
- El PIN se guarda con hash (argon2-cffi). Se bloquea tras 5 intentos fallidos
  durante 15 minutos, porque 4 cifras se pueden probar todas por fuerza bruta.
- Anonimato: la API nunca envía al receptor el id ni el nombre de quien le regala,
  ni por REST ni por websocket. Debe haber tests que lo comprueben.
- Despliegue: Docker Compose en el VPS (caddy, api, postgres). Caddy da HTTPS
  automático, que es obligatorio para el service worker y las push; sirve el
  `dist/` de la web como estáticos (con `try_files` a `index.html` para las rutas
  de la SPA) y hace de proxy de `/api` y de los websockets hacia FastAPI.

## Algoritmo de sorteo
- Asignación aleatoria en la que nadie se toca a sí mismo y se respetan
  las exclusiones (simétricas).
- Backtracking aleatorizado; con grupos de hasta 50 personas es suficiente.
- Bajas después del sorteo (`close_gap`): quien regalaba a la persona que se va pasa a
  regalar a quien ella regalaba. Si eso no vale (exclusión o pareja de dos), se cruza con
  otra pareja al azar. Cambian dos personas como mucho y se les avisa por push.
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
1. Inicio: una ventana con celosía que tapa un nombre (solo se lee donde pasas
   el dedo), titular, formulario para crear grupo y enlace a "Probar la demo".
2. Compartir: enlace del grupo y botón de WhatsApp con el mensaje ya redactado.
3. Unirse: nombre + PIN, con la explicación de para qué sirve el PIN.
4. Sala de espera: apuntados, lista de deseos y, si eres el organizador,
   exclusiones y "Hacer el sorteo".
5. Revelado: el nombre está detrás de una celosía de dos hojas que se abren.
   Debajo, la lista de deseos y "Preguntarle algo en secreto".
6. Chat: dos pestañas, "escribiendo…", "leído" y no leídos. Quien te escribe
   aparece como una ventanita de celosía, nunca con nombre ni iniciales.
7. Activar avisos: se ofrece tras el primer mensaje recibido, con el paso a paso
   para iPhone.

## Dirección visual
Detalle completo en `apps/web/DESIGN.md`. Resumen:
- Concepto: la celosía. Ver sin ser visto, como tras la celosía de un patio
  andaluz. Lo secreto está detrás de la celosía y solo se lee donde da la luz;
  revelar es abrirla. La celosía (estrella de ocho puntas, `src/assets/lattice.svg`
  usada como máscara CSS) es el único ornamento.
- Colores (variables en `apps/web/src/globals.css`): añil #1D2A8C de fondo,
  añil claro #2A3AA6 para bloques, sombra #0B1150 para campos y lo que hay detrás
  de la celosía, cal #F5F0E6 para texto y madera, texto secundario #C8CDEE y
  albero #F0B43A como única luz caliente: acción principal y lo revelado.
- Tipografía: Reem Kufi en titulares (600–700, interletraje −0,025 em);
  Onest en la interfaz, entre 15 y 17 px.
- Formas: botones en píldora; campos con 12 px de radio; bloques con 22 px y sin
  borde. Sin sombras ni degradados decorativos.
- Texto: frases en minúscula, sin etiquetas en mayúsculas y sin flechas en los
  botones.
- Movimiento: la luz que recorre la celosía del inicio, las hojas que se abren
  en el revelado (con su sombra resbalando sobre el nombre) y las escenas de «así
  funciona» en la portada, que cambian con el scroll. Nada más.
  Respetar prefers-reduced-motion.
- Referencia: boceto interactivo de la celosía (inicio, revelado y chat),
  elegido el 10-nov-2026 entre tres propuestas.

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
   Commit: "feat: lobby, wishlist and exclusions". HECHA.
3. Sorteo y revelado: algoritmo con tests de Hypothesis y pantalla de revelado
   con la animación de la celosía que se abre.
   Verificable: tests verdes y caso imposible gestionado.
   Commit: "feat: constrained draw and reveal". HECHA.
4. Chat asíncrono: endpoints REST, persistencia y no leídos, más tests de que
   no se filtra la identidad.
   Verificable: el receptor nunca recibe el giver_id.
   Commit: "feat: anonymous async chat". HECHA.
5. Tiempo real: websockets, ConnectionManager, "escribiendo…" y "leído".
   Verificable: dos navegadores ven los cambios en vivo.
   Commit: "feat: realtime chat via websockets". HECHA.
6. PWA y push: manifest, service worker, VAPID, suscripciones y ayuda para iOS.
   Iconos de la app a partir de `apps/web/public/favicon.svg` (estrella albero
   sobre añil): apple-touch-icon 180 a sangre (sin esquinas), 192, 512 y maskable.
   Verificable: llega una push en Android y en un iPhone con la web instalada.
   Commit: "feat: PWA and web push". HECHA (pendiente la prueba en móvil con HTTPS).
7. Pulido visual y modo demo.
   Verificable: alguien ajeno lo entiende y lo prueba en menos de un minuto.
   Commit: "feat: visual polish and demo mode". HECHA (pendiente la prueba con
   alguien ajeno). La demo (`POST /demo`) crea un grupo propio por visita, ya sorteado,
   con cuatro personas y una conversación empezada entre Lucía y Mario; en grupos con
   `demo = true` se cambia de persona sin PIN y se borran pasado un día.
8. Despliegue y README.
   Verificable: funciona por HTTPS en el subdominio y el README está completo.
   Commit: "docs: README and deploy". HECHA en el repo (pendiente el despliegue real).
   `deploy/`: docker-compose.yml (caddy, api, db), Caddyfile y web.Dockerfile (compila
   la web y la sirve con Caddy); `apps/api/Dockerfile` aplica migraciones al arrancar.

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
