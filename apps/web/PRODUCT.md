# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Grupos de amigos, familias y compañeros de trabajo en España que organizan un amigo invisible por Navidad. El organizador lo monta desde el móvil y comparte un enlace por WhatsApp; el resto entra desde ese enlace, casi siempre en el móvil, a menudo sin muchas ganas de "instalar algo" ni crear cuentas.

## Product Purpose
psst organiza un amigo invisible gratis y sin cuentas: crear grupo, compartir enlace, unirse con nombre + PIN, sorteo con exclusiones y revelado de a quién regalas con su lista de deseos. Éxito: un grupo real lo usa de principio a fin antes de Navidad y alguien ajeno entiende la demo en menos de un minuto.

## Positioning
Chat anónimo entre quien regala y quien recibe: puedes preguntarle a tu persona qué quiere sin que sepa quién eres. La API nunca envía al receptor la identidad de quien le regala.

## Operating Context
Enlace compartido por WhatsApp, uso móvil, PWA instalable con notificaciones push (en iOS solo instalada). Momentos clave: unirse, el revelado (el momento emocional) y el chat con dos conversaciones ("quien te regala", anónima, y "a quien regalas").

## Capabilities and Constraints
- Sin email, teléfono ni cuentas; nombre + PIN de 4 cifras (bloqueo tras 5 intentos).
- Grupo: nombre, presupuesto, fecha. Organizador también participa, define exclusiones, cierra inscripciones y sortea.
- Chat en tiempo real: "escribiendo…", "leído", no leídos. Quien te escribe nunca aparece con nombre ni iniciales.
- Modo demo con grupo ya sorteado y cambio entre dos participantes.
- Stack: Vite + React + CSS Modules; fuentes autoalojadas (funciona offline como PWA).
- Fuera de alcance v1: cuentas, idiomas, app nativa, modo disfraz con IA.

## Brand Commitments
Nombre "psst". Voz en español, cercana, frases en minúscula. El 10-nov-2026 el usuario descartó la dirección visual anterior (vino/rosa, barra de censura, Archivo): todo lo visual queda libre.

## Evidence on Hand
Sin usuarios reales, testimonios ni métricas todavía: no inventarlos. Contenido de demo permitido si se marca como ejemplo.

## Product Principles
- Cero fricción: un enlace, un nombre, un PIN.
- El secreto es sagrado: nada en la interfaz puede insinuar quién regala.
- El revelado es un momento, no un dato.
- Se entiende en un minuto, sin instrucciones.

## Accessibility & Inclusion
Respetar prefers-reduced-motion; contraste AA; campos de 16 px en móvil para evitar zoom en iOS.
