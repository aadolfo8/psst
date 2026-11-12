# apps/web — instrucciones para Claude Code

- React Router (v8) y Vite (v8) pueden diferir de lo que conoces: consulta
  `node_modules/react-router/docs/` antes de usar APIs que no tengas claras.

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
