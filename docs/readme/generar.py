"""Genera las ilustraciones SVG del README con las fuentes incrustadas en base64.

Uso, desde la raíz del repo y con `pnpm install` hecho: `python docs/readme/generar.py .`
"""

import base64
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
FONTS = ROOT / "apps/web/node_modules/@fontsource-variable"
OUT = ROOT / "docs/readme"
OUT.mkdir(parents=True, exist_ok=True)


def font(path: str, family: str) -> str:
    data = base64.b64encode((FONTS / path).read_bytes()).decode()
    return (
        f"@font-face{{font-family:'{family}';font-weight:400 700;"
        f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
    )


KUFI = font("reem-kufi/files/reem-kufi-latin-wght-normal.woff2", "Kufi")
ONEST = font("onest/files/onest-latin-wght-normal.woff2", "Onest")

ANIL, ANIL2, SOMBRA, CAL, CAL2, ALBERO = (
    "#1D2A8C", "#2A3AA6", "#0B1150", "#F5F0E6", "#C8CDEE", "#F0B43A",
)

# Pieza de la celosía (46x46): madera opaca, estrella y rombos huecos.
TILE = (
    "M0 0H46V46H0ZM23 6L27.98 10.98L35.02 10.98L35.02 18.02L40 23L35.02 27.98L35.02 35.02"
    "L27.98 35.02L23 40L18.02 35.02L10.98 35.02L10.98 27.98L6 23L10.98 18.02L10.98 10.98"
    "L18.02 10.98ZM0 -6L6 0L0 6L-6 0ZM46 -6L52 0L46 6L40 0ZM0 40L6 46L0 52L-6 46Z"
    "M46 40L52 46L46 52L40 46Z"
)
STAR = "M32 12.2L37.8 18H46V26.2L51.8 32L46 37.8V46H37.8L32 51.8L26.2 46H18V37.8L12.2 32L18 26.2V18H26.2Z"


def lattice_pattern(pid: str, size: float = 46, color: str = CAL) -> str:
    s = size / 46
    return (
        f'<pattern id="{pid}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">'
        f'<path transform="scale({s})" fill="{color}" fill-rule="evenodd" d="{TILE}"/></pattern>'
    )


def star(x: float, y: float, size: float, color: str = ALBERO) -> str:
    s = size / 64
    return f'<path transform="translate({x} {y}) scale({s}) translate(-32 -32)" fill="{color}" d="{STAR}"/>'


def svg(w: int, h: int, fonts: str, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{title}"><title>{title}</title>'
        f"<style>{fonts}"
        ".k{font-family:Kufi,'Segoe UI',sans-serif;letter-spacing:-0.025em;word-spacing:.1em}"
        ".o{font-family:Onest,'Segoe UI',sans-serif}"
        "@media (prefers-reduced-motion:reduce){animate,animateMotion{display:none}}"
        f"</style>{body}</svg>\n"
    )


# ---------- Cabecera: título y ventana de celosía con la luz paseando ----------
hero = f"""
<defs>
  {lattice_pattern("lat", 92)}
  <radialGradient id="light">
    <stop offset="0" stop-color="#fff"/>
    <stop offset=".55" stop-color="#fff" stop-opacity=".75"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glow">
    <stop offset="0" stop-color="{ANIL2}"/>
    <stop offset="1" stop-color="{SOMBRA}" stop-opacity="0"/>
  </radialGradient>
  <mask id="lightmask" maskUnits="userSpaceOnUse" x="0" y="0" width="1280" height="440">
    <circle r="210" fill="url(#light)">
      <animateMotion dur="9s" repeatCount="indefinite" calcMode="spline"
        keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"
        path="M790 170 C900 120 1060 300 1170 230 C1060 330 900 120 790 170"/>
    </circle>
  </mask>
  <clipPath id="win"><rect x="700" y="60" width="520" height="320" rx="22"/></clipPath>
</defs>
<rect width="1280" height="440" rx="28" fill="{ANIL}"/>

{star(108, 112, 64)}
<text x="80" y="236" class="k" font-size="112" font-weight="700" fill="{CAL}">psst</text>
<text x="84" y="292" class="o" font-size="27" font-weight="500" fill="{CAL}">el amigo invisible por enlace,</text>
<text x="84" y="328" class="o" font-size="27" font-weight="500" fill="{CAL}">con un chat <tspan fill="{ALBERO}">secreto</tspan> entre quien</text>
<text x="84" y="364" class="o" font-size="27" font-weight="500" fill="{CAL}">regala y quien recibe.</text>

<g clip-path="url(#win)">
  <rect x="700" y="60" width="520" height="320" fill="{SOMBRA}"/>
  <g mask="url(#lightmask)">
    <rect x="700" y="60" width="520" height="320" fill="url(#glow)"/>
    <text x="960" y="272" text-anchor="middle" class="k" font-size="150" font-weight="700" fill="{ALBERO}">Mario</text>
  </g>
  <rect x="700" y="60" width="520" height="320" fill="url(#lat)"/>
</g>
"""
(OUT / "hero.svg").write_text(
    svg(1280, 440, KUFI + ONEST, hero, "psst: el amigo invisible con chat secreto"), "utf-8"
)


# ---------- El chat visto desde los dos lados ----------
def bubble(x: float, y: float, text: str, mine: bool, width: float) -> str:
    fill, color = (CAL, SOMBRA) if mine else (ANIL2, CAL)
    bx = x + (390 - width) if mine else x
    return (
        f'<rect x="{bx}" y="{y}" width="{width}" height="46" rx="20" fill="{fill}"/>'
        f'<text x="{bx + 20}" y="{y + 29.5}" class="o" font-size="17" fill="{color}">{text}</text>'
    )


def phone(x: float, label: str, tab_active: int, who: str, avatar: str, msgs: list, foot: str) -> str:
    out = [
        f'<text x="{x + 215}" y="58" text-anchor="middle" class="o" font-size="18" fill="{CAL2}">{label}</text>',
        f'<rect x="{x}" y="80" width="430" height="440" rx="34" fill="{ANIL}"/>',
        f'<rect x="{x}" y="80" width="430" height="34" fill="url(#lat2)" clip-path="url(#ph{int(x)})"/>',
    ]
    tabs = ["quien te regala", "a quien regalas"]
    tx = x + 20
    for i, t in enumerate(tabs):
        w = 182
        if i == tab_active:
            out.append(f'<rect x="{tx}" y="132" width="{w}" height="38" rx="19" fill="{CAL}"/>')
            out.append(
                f'<text x="{tx + w / 2}" y="157" text-anchor="middle" class="o" font-size="15.5" '
                f'font-weight="600" fill="{SOMBRA}">{t}</text>'
            )
        else:
            out.append(
                f'<text x="{tx + w / 2}" y="157" text-anchor="middle" class="o" font-size="15.5" fill="{CAL2}">{t}</text>'
            )
        tx += w + 10
    out.append(avatar)
    out.append(f'<text x="{x + 86}" y="214" class="k" font-size="23" font-weight="600" fill="{CAL}">{who}</text>')
    out.append(f'<line x1="{x + 20}" x2="{x + 410}" y1="244" y2="244" stroke="{CAL}" stroke-opacity=".2"/>')
    y = 262
    for text, mine, w in msgs:
        out.append(bubble(x + 20, y, text, mine, w))
        y += 58
    out.append(f'<text x="{x + 410}" y="{y + 8}" text-anchor="end" class="o" font-size="14" fill="{CAL2}">{foot}</text>')
    return "\n".join(out)


lat_avatar = (
    f'<g clip-path="url(#av)"><rect x="728" y="180" width="46" height="46" fill="{SOMBRA}"/>'
    f'<rect x="728" y="180" width="46" height="46" fill="url(#lat3)"/></g>'
)
name_avatar = (
    f'<circle cx="103" cy="203" r="23" fill="{ALBERO}"/>'
    f'<text x="103" y="211" text-anchor="middle" class="k" font-size="22" font-weight="700" fill="{SOMBRA}">M</text>'
)

conv = [
    ("psst. ¿qué talla de jersey usas?", True, 290),
    ("una m. ¿quién eres?", False, 196),
    ("eso no se pregunta.", True, 190),
    ("¿más de té o de café?", True, 214),
]
# Para quien recibe, los mismos mensajes con los lados cambiados.
mirror = [(t, not m, w) for t, m, w in conv]

chat = f"""
<defs>
  {lattice_pattern("lat2", 34)}
  <pattern id="lat3" x="728" y="180" width="46" height="46" patternUnits="userSpaceOnUse">
    <path fill="{CAL}" fill-rule="evenodd" d="{TILE}"/></pattern>
  <clipPath id="ph80"><rect x="80" y="80" width="430" height="440" rx="34"/></clipPath>
  <clipPath id="ph705"><rect x="705" y="80" width="430" height="440" rx="34"/></clipPath>
  <clipPath id="av"><rect x="728" y="180" width="46" height="46" rx="14"/></clipPath>
</defs>
<rect width="1215" height="600" rx="28" fill="{SOMBRA}"/>
{phone(80, "lo que ve Lucía, que regala", 1, "Mario", name_avatar, conv, "leído")}
{phone(705, "lo que ve Mario, que recibe", 0, "tu amigo invisible", lat_avatar, mirror, "")}
<g transform="translate(607.5 300)">
  {star(0, 0, 54)}
</g>
<text x="607.5" y="566" text-anchor="middle" class="o" font-size="18" fill="{CAL2}">la misma conversación: Mario nunca recibe el nombre ni el id de quien le escribe.</text>
"""
(OUT / "chat.svg").write_text(
    svg(1215, 600, KUFI + ONEST, chat, "El chat anónimo visto desde los dos lados"), "utf-8"
)


# ---------- Los pasos ----------
steps = [
    ("crea", "el grupo"),
    ("comparte", "por WhatsApp"),
    ("únete", "nombre y PIN"),
    ("sorteo", "con exclusiones"),
    ("abre", "la celosía"),
    ("pregunta", "en secreto"),
]
cards = []
for i, (a, b) in enumerate(steps):
    x = 20 + i * 205
    last = i == 5
    cards.append(f'<rect x="{x}" y="20" width="190" height="170" rx="22" fill="{ANIL2 if not last else ANIL}"/>')
    cards.append(
        f'<text x="{x + 24}" y="76" class="k" font-size="40" font-weight="700" fill="{ALBERO}">{i + 1}</text>'
    )
    cards.append(f'<text x="{x + 24}" y="128" class="k" font-size="27" font-weight="600" fill="{CAL}">{a}</text>')
    cards.append(f'<text x="{x + 24}" y="158" class="o" font-size="17" fill="{CAL2}">{b}</text>')
    if last:
        cards.append(
            f'<rect x="{x}" y="20" width="190" height="170" rx="22" fill="none" stroke="{ALBERO}" stroke-width="2"/>'
        )
steps_svg = f'<rect width="1250" height="210" rx="28" fill="{SOMBRA}"/>' + "".join(cards)
(OUT / "pasos.svg").write_text(
    svg(1250, 210, KUFI + ONEST, steps_svg, "Cómo funciona psst en seis pasos"), "utf-8"
)

for f in sorted(OUT.iterdir()):
    print(f.name, f.stat().st_size)
