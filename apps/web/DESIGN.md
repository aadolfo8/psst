# psst — sistema visual: la celosía

Ver sin ser visto, como tras la celosía de un patio andaluz. Lo secreto está detrás de la
celosía y solo se lee donde da la luz; revelar es abrirla. Elegido el 10-nov-2026 entre tres
bocetos (celosía, bombo de lotería y clásico navideño).

## Color

Estrategia comprometida: el añil ocupa toda la superficie; el albero es la única luz caliente.

| Token | Valor | Uso |
|---|---|---|
| `--anil` | #1D2A8C | fondo de todas las pantallas |
| `--anil-2` | #2A3AA6 | bloques, burbujas de la otra persona en el chat |
| `--sombra` | #0B1150 | campos, etiquetas, lo que hay detrás de la celosía |
| `--cal` | #F5F0E6 | texto, madera de la celosía, tus burbujas en el chat |
| `--cal-2` | #C8CDEE | texto secundario, etiquetas de campos |
| `--albero` | #F0B43A | acción principal, lo revelado, no leídos, foco, selección |
| `--linea` | cal al 20 % | separadores de listas, borde de botones secundarios |
| `--error` | #FFB4A8 | texto de error sobre `--sombra` |

Regla: el albero no decora. Si algo es albero es porque es lo que hay que pulsar o lo que
se acaba de descubrir.

## Tipografía

- **Reem Kufi** (variable, 400–700): logotipo, titulares y subtítulos. Peso 700 en
  titulares, 600 en subtítulos, interletraje −0,025 em y `word-spacing: 0.1em` (sus espacios
  son estrechos).
- **Onest** (variable, 400–700): toda la interfaz, entre 15 y 17 px; los campos a 16 px para
  que iOS no haga zoom.
- Ambas autoalojadas con fontsource.

## La celosía

- Pieza: `src/assets/lattice.svg`, 46 × 46 px. Estrella de ocho puntas en el centro y rombos
  en las esquinas como huecos. Se usa como máscara CSS en mosaico (`--lattice-tile`,
  `--lattice-size`).
- Clase `.lattice` en `ui.module.css`: un bloque color cal enmascarado; lo que hay detrás se
  ve por los huecos.
- Usos:
  - **Inicio** (`LatticeWindow`): ventana a todo lo ancho con un nombre en albero detrás.
    Una segunda máscara radial abre un círculo de luz que sigue al dedo; sin interacción,
    pasea sola. Con `prefers-reduced-motion` se queda quieta en el centro.
  - **Pantallas interiores**: friso de celosía de 46 px a todo lo ancho, arriba del todo.
  - **Revelado** (fase 3): dos hojas de celosía sobre el nombre; al pulsar "abrir la
    celosía" giran en 3D hacia fuera (1,25 s, `cubic-bezier(.6,.05,.2,1)`), el nombre pasa de
    desenfocado a nítido y la sombra de la celosía resbala sobre él y se desvanece. Después
    entran presupuesto, fecha, lista de deseos y "preguntarle algo en secreto".
  - **Chat** (fases 4 y 5): quien te regala tiene como avatar una ventanita de celosía sobre
    sombra, nunca nombre ni inicial. "escribiendo…" son tres estrellas de cuatro puntas que
    titilan.

## Componentes

- **Botón principal**: píldora albero, texto sombra, 17 px seminegrita. Al pulsar, escala 0,98.
- **Botón secundario**: píldora transparente con borde interior de 1,5 px en `--linea`; al
  pasar, el borde pasa a cal.
- **Campos**: fondo sombra, sin borde visible, radio 12 px; al enfocar, borde albero de 1,5 px.
  `color-scheme: dark` para los controles nativos.
- **PIN**: un solo campo, Reem Kufi 26 px, espaciado ancho.
- **Bloques**: fondo añil claro, radio 22 px, sin borde ni sombra.
- **Etiquetas** ("tú", "organiza"): píldoras pequeñas en sombra con texto cal-2.
- **Chat**: pestañas en una píldora sombra, la activa en cal. Burbujas de 18 px de radio con la
  esquina de la cola a 6 px; las tuyas en cal, las ajenas en añil claro. "leído" en cal-2 con
  doble check.

## Composición

- Móvil primero: columna de 480 px como máximo con margen de 22 px.
- Inicio en escritorio (≥ 860 px): ventana de celosía a todo lo ancho; debajo, titular a la
  izquierda (fijo al hacer scroll) y formulario a la derecha, en un ancho máximo de 1040 px.

## Movimiento

Solo dos momentos: la luz que recorre la celosía del inicio y las hojas que se abren en el
revelado. Los mensajes nuevos del chat entran con un pequeño salto (0,45 s) y, mientras el
navegador instala la app, la estrella del aviso late despacio. Todo respeta
`prefers-reduced-motion`.

## Texto

Frases en minúscula, sin etiquetas en mayúsculas, sin flechas en los botones. Los textos de
ayuda en frase normal.
