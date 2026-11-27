"""Marca do site: símbolo (livro aberto + folhas tricolores), nome empilhado e troféus em silhueta.

Tudo é SVG desenhado para este projeto (nenhum arquivo de terceiros). Para trocar o nome exibido,
altere BRAND_TOP / BRAND_BOTTOM; para usar outro símbolo, troque LOGO_SVG.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

GREEN, GREEN_2, GARNET, GARNET_2 = "#006B3F", "#0A8A55", "#7A0019", "#9B1B30"

BRAND_TOP = "Wikipédia"
BRAND_BOTTOM = "Tricolor"
TAGLINE = "Enciclopédia do Fluminense Football Club"

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Livro aberto grená com três folhas/chamas verdes saindo das páginas.
LOGO_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="{BRAND_TOP} {BRAND_BOTTOM}">
<path d="M50 54 C41 43 39 25 50 6 C61 25 59 43 50 54Z" fill="{GREEN}"/>
<path d="M47 56 C33 53 20 42 15 22 C32 25 44 37 47 56Z" fill="{GREEN_2}"/>
<path d="M53 56 C67 53 80 42 85 22 C68 25 56 37 53 56Z" fill="{GREEN_2}"/>
<path d="M50 64 C40 56 24 54 6 57 L6 89 C24 86 40 88 50 96Z" fill="{GARNET}"/>
<path d="M50 64 C60 56 76 54 94 57 L94 89 C76 86 60 88 50 96Z" fill="{GARNET_2}"/>
<path d="M12 64 C25 62 37 63 45 69 M12 72 C25 70 37 71 45 77 M12 80 C25 78 37 79 45 85" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".8"/>
<path d="M88 64 C75 62 63 63 55 69 M88 72 C75 70 63 71 55 77 M88 80 C75 78 63 79 55 85" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".8"/>
</svg>"""


def data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def lockup(variant: str = "light", size: str = "md") -> str:
    """Símbolo + nome empilhado. variant: 'light' (fundo claro) | 'dark' (fundo verde/escuro)."""
    return (f'<div class="wf-lockup {variant} {size}">'
            f'<span class="mark"><img src="{data_uri(LOGO_SVG)}" alt=""></span>'
            f'<span class="name"><b>{BRAND_TOP}</b><i>{BRAND_BOTTOM}</i></span></div>')


def hamburger_uri(color: str) -> str:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g stroke="{color}" '
           'stroke-width="2.2" stroke-linecap="round"><path d="M4 6.5h16M4 12h16M4 17.5h16"/></g></svg>')
    return data_uri(svg)


# ----------------------------------------------------------------------------- troféus
# Silhuetas estilizadas (viewBox 40×64), desenhadas a partir da forma atual de cada troféu.
_S = 'fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"'
TROPHIES = {
    # Libertadores: taça prateada com a figura de um jogador na tampa, sobre base alta.
    "libertadores": f"""<circle cx="20" cy="3.6" r="2.6"/><path d="M17 7h6l1 5-1.5.6 1.8 5h-2.2l-1.6-4-1.6 4h-2.2l1.8-5L16 12z"/>
<ellipse cx="20" cy="20" rx="7.5" ry="2.4"/><path d="M10 21.5h20c0 9-4 14.5-10 15.5-6-1-10-6.5-10-15.5z"/>
<path {_S} d="M10.5 23.5c-5.5 0-5.5 8 1.5 8.5M29.5 23.5c5.5 0 5.5 8-1.5 8.5"/>
<path d="M17.5 37h5v4h-5z"/><path d="M12 41h16l1.5 21h-19z"/>""",
    # Recopa Sul-Americana: bola dourada sobre coluna, base preta escalonada (modelo atual).
    "recopa": """<circle cx="20" cy="9" r="8"/><path d="M15 17.5h10l-2 4.5h-6z"/>
<path d="M17.6 22h4.8v14h-4.8z"/><path d="M15 25.5h10v2.4H15zM15 31.5h10v2.4H15z"/>
<path d="M11.5 36h17v2.6h-17z"/><path d="M8.5 38.6h23l4 23.4h-31z"/>""",
    # Copa Rio 1952: urna clássica com tampa e alças (troféu único).
    "copario": f"""<circle cx="20" cy="3.5" r="2.2"/><path d="M13.5 12c1-4.5 3.5-6.5 6.5-6.5s5.5 2 6.5 6.5z"/>
<path d="M11 13h18c.5 11-3 18.5-9 20-6-1.5-9.5-9-9-20z"/><path {_S} d="M11.5 15c-6 0-6.5 10 1 11M28.5 15c6 0 6.5 10-1 11"/>
<path d="M18 33h4v12h-4z"/><path d="M14 45h12v3H14z"/><path d="M11 48h18l2 14H9z"/>""",
    # Brasileirão: taça esguia, sem alças, de boca larga, sobre pedestal em dois níveis.
    "brasileiro": """<path d="M7 4h26c-1 13-5.5 21-11 24v2h-4v-2C12.5 25 8 17 7 4z"/><ellipse cx="20" cy="32" rx="4.5" ry="2"/>
<path d="M18.2 33h3.6v13h-3.6z"/><path d="M13 46h14v4H13z"/><path d="M10 50h20l2 12H8z"/>""",
    # Copa do Brasil: taça larga de alças grandes, pé curto e base cilíndrica.
    "copadobrasil": f"""<path d="M9 6h22c0 14-4.5 22-11 24-6.5-2-11-10-11-24z"/><path {_S} d="M9.5 8C1 8 1 24 13.5 26M30.5 8C39 8 39 24 26.5 26"/>
<path d="M18 30h4v10h-4z"/><path d="M12.5 40h15v3h-15z"/><path d="M10 43h20v19H10z"/>""",
    # Série C: cálice simples.
    "seriec": f"""<path d="M10 8h20c0 12-4 18-10 20-6-2-10-8-10-20z"/><path {_S} d="M10.5 10c-5 0-5 9 2 10M29.5 10c5 0 5 9-2 10"/>
<path d="M18 28h4v14h-4z"/><path d="M12 42h16l2 20H10z"/>""",
    # Rio-São Paulo: taça com tampa pontuda.
    "riosp": f"""<path d="M20 1l3 6h-6z"/><path d="M13 11.5c1-3 3.5-4.5 7-4.5s6 1.5 7 4.5z"/><path d="M11 12.5h18c0 11-4 17-9 18.5-5-1.5-9-7.5-9-18.5z"/>
<path {_S} d="M11.5 14c-5 0-5 9 2 10M28.5 14c5 0 5 9-2 10"/><path d="M18 31h4v13h-4z"/><path d="M12 44h16l2 18H10z"/>""",
    # Campeonato Carioca: taça alta e afunilada, com coroa estilizada e base larga.
    "carioca": """<path d="M12 2l2.5 4L17 2l3 4 3-4 2.5 4L28 2v6H12z"/><path d="M11 9h18c-.5 12-3.5 20-9 23-5.5-3-8.5-11-9-23z"/>
<path d="M18.2 32h3.6v12h-3.6z"/><ellipse cx="20" cy="45" rx="7" ry="2"/><path d="M9 47h22l2 15H7z"/>""",
}


def trophy_svg(key: str) -> str:
    return (f'<svg viewBox="0 0 40 64" fill="currentColor" xmlns="http://www.w3.org/2000/svg" '
            f'aria-hidden="true">{TROPHIES.get(key, TROPHIES["seriec"])}</svg>')


@lru_cache(maxsize=4)
def image_b64(name: str) -> str:
    p = ASSETS / name
    return base64.b64encode(p.read_bytes()).decode("ascii") if p.exists() else ""
