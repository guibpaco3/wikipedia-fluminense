"""Parser das páginas de resultados da RSSSF (texto livre).

Reconhece os formatos encontrados nas páginas usadas pelo projeto:

  Cabeçalhos de data   [Jan 17]   [Aug 24 and 31]   (Aug 12 and 26)   [Oct 21] - playoff   1. 7.1984
  Jogo simples         Fluminense      2-1  Santos            (data do cabeçalho)
                       03/May - Paysandu 1-7 Fluminense (Rua Guanabara).
                       23/Sep      Portuguesa 1-4 América
                       Feb 20: LDU Quito - Fluminense      0-0
                       23 Jul: Fluminense - Vasco da Gama  3-3
                       Fluminense 2-1 Portuguesa [played in Moça Bonita, Rio de Janeiro-RJ]
  Ida e volta          Fonseca         0-3   0-8  Fluminense          (datas do cabeçalho)
                       13 Adesg (AC) - Fluminense (RJ)   1-2 (14/02)   0-6 (28/02)
                       Alianza Atlético  Per  Fluminense  Bra   2-2  1-4  3-6x

Nos jogos de ida e volta os dois placares são escritos do ponto de vista do primeiro
clube da linha (convenção da RSSSF); o jogo de volta é no campo do segundo clube.

Ano das datas sem ano: o da temporada da página; datas em meses ANTERIORES ao mês do
primeiro jogo datado da página pertencem ao ano seguinte (temporadas que viram o ano).

O parser não adivinha: jogo sem data inequívoca vai para `undated`; linha do Fluminense
com placar que não casa com nenhum formato vai para `unparsed`; W.O., jogos anulados e
"Fluminense" ambíguo (página que também tem o Fluminense de Feira etc.) vão para `ambiguous`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from collectors.teams import FIFA_ISO2, is_fluminense, split_name
from core.text import norm

_MONTH_NAMES = {
    1: "january jan janeiro", 2: "february feb fev fevereiro", 3: "march mar março marco",
    4: "april apr abr abril", 5: "may mai maio", 6: "june jun junho", 7: "july jul julho",
    8: "august aug ago agosto", 9: "september sept sep set setembro", 10: "october oct out outubro",
    11: "november nov novembro", 12: "december dec dez dezembro",
}
MONTHS = {w: n for n, ws in _MONTH_NAMES.items() for w in ws.split()}
_MON = r"(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?(?![a-zà-ÿ])"
_MON_RX = re.compile(_MON, re.I)

_D_SLASH_MON = rf"(?P<d1>\d{{1,2}})/(?P<m1>{_MON})(?:/(?P<y1>\d{{2,4}}))?"     # 03/May  02/Jan/1955  20/sep/87
_D_MON_D = rf"(?P<m2>{_MON})\s+(?P<d2>\d{{1,2}})(?:,?\s+(?P<y2>\d{{4}}))?"       # Feb 20 / Feb 20, 1985
_D_D_MON = rf"(?P<d3>\d{{1,2}})\s+(?P<m3>{_MON})(?:\s+(?P<y3>\d{{4}}))?"         # 23 Jul
_D_NUM = r"(?P<d4>\d{1,2})\s*[./]\s*(?P<m4>\d{1,2})(?:\s*[./]\s*(?P<y4>\d{2,4}))?(?=\s)"  # 14/02  1. 7.1984  19 / 05
_LEADING_DATE = re.compile(
    rf"^\s*(?:{_D_SLASH_MON}|{_D_MON_D}|{_D_D_MON}|{_D_NUM})"
    rf"\s*?(?:\s*[:\-–]\s*|\s{{2,}}|\t+|\s+(?=[A-ZÀ-Ý]))", re.I)
_HEADER = re.compile(r"^\s*[\[(]?\s*(?P<body>[^\[\]()]*?)\s*[\])]?\s*(?:-\s*[A-Za-z ]+)?\s*$")
_DATE_ITEM = rf"(?:{_MON}\s+)?\d{{1,2}}(?:\s*{_MON})?(?:,?\s+\d{{4}})?"
_ONLY_DATES = re.compile(
    rf"^(?:\d{{1,2}}\s*[./]\s*\d{{1,2}}(?:\s*[./]\s*\d{{2,4}})?|"
    rf"{_DATE_ITEM}(?:\s*(?:and|e|&|,|/|-|–)\s*{_DATE_ITEM})*)$", re.I)
_NUM_DATE_LINE = re.compile(r"^\d{1,2}\s*[./]\s*\d{1,2}(?:\s*[./]\s*\d{2,4})?\.?$")
# Ficha de jogo (RSSSF Brasil): "Data – 27 / 10 / 1912", "Local – Laranjeiras (Rio de Janeiro – RJ)", "Árbitro – X"
_SHEET_DATE = re.compile(r"^Data\s*[–:-]\s*(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(\d{4})\b", re.I)
_SHEET_PLACE = re.compile(r"^Local\s*[–:-]\s*(?P<v>[^(]+?)\s*(?:\((?P<city>[^)–-]+)(?:\s*[–-]\s*[A-Z]{2})?\))?\s*\.?$", re.I)
_SHEET_REF = re.compile(r"^[ÁA]rbitro\s*[–:-]\s*(?P<r>[^.;(]+?)\s*\.?$", re.I)
# Detalhe de jogo (finais/Recopa): "First leg [Feb 22, Estadio X, Quito, Ecuador, att: 30.700, ref: Fulano (Colombia)"
_DETAIL = re.compile(
    rf"^(?:(?:first|second|third|1st|2nd|3rd)\s+)?(?:leg|match|game|replay|final|playoff|play-off)?\s*"
    rf"\[\s*(?P<date>{_MON}\s+\d{{1,2}}(?:,?\s+\d{{4}})?)\s*,\s*(?P<body>[^\]]*)\]?\s*$", re.I)

_TEAM = r"[^\d\[\]{}|\t]*?[^\d\s\[\]{}|\-–:]"
_SCORE = r"(?P<{0}h>\d{{1,2}})\s?[-xX×]\s?(?P<{0}a>\d{{1,2}})"
# Resto da linha após o 2º clube: vazio, ou começa com [ ( * ou marcas de prorrogação/pênaltis.
# "(RJ)"/"(ARG)" logo após o nome fazem parte do nome, não do resto.
_REST = (r"\s*(?P<rest>(?:(?:[-–]\s*)?(?!\(\s*[A-Z]{2,3}\s*\))[\[(*].*|"
         r"(?:a\.?e\.?t\.?|aet|asdet|x|p|pen|prorr\w*)(?:\W.*)?)?)$")


def _sc(tag: str) -> str:
    return _SCORE.format(tag)


_CC = r"[A-Z][a-z]{2}"
P_TWO_LEG_DATED = re.compile(
    rf"^(?:(?:\d{{1,3}}|[A-Z])\s+)?(?P<a>{_TEAM})\s+(?:-|x)\s+(?P<b>{_TEAM})\s+"
    rf"(?:{_sc('s')}|(?P<np1>n/?p|w\.?o\.?))\s*\((?P<dt1>[^)]+)\)\s+"
    rf"(?:{_sc('t')}|(?P<np2>n/?p|w\.?o\.?))\s*\((?P<dt2>[^)]+)\)(?P<rest>.*)$", re.I)
_SEP_CC = r"(?:\s+|(?<=\)))"     # "Fluminense (R. de Janeiro)Bra": código colado ao parêntese
P_TWO_LEG_CC = re.compile(
    rf"^(?P<a>{_TEAM}){_SEP_CC}(?P<ca>{_CC})\s+(?P<b>{_TEAM}){_SEP_CC}(?P<cb>{_CC})\s+{_sc('s')}\s+{_sc('t')}"
    rf"(?P<rest>.*)$")
P_ONE_LEG_CC = re.compile(
    rf"^(?P<a>{_TEAM}){_SEP_CC}(?P<ca>{_CC})\s+(?P<b>{_TEAM}){_SEP_CC}(?P<cb>{_CC})\s+{_sc('s')}"
    rf"(?P<rest>(?:\s+\S+)?)\s*$")
P_TWO_LEG = re.compile(rf"^(?P<a>{_TEAM})\s+{_sc('s')}\s+{_sc('t')}\s+(?P<b>{_TEAM}){_REST}")
P_DASH = re.compile(rf"^(?P<a>{_TEAM})\s+[-–]\s+(?P<b>{_TEAM})\s+{_sc('s')}(?P<rest>(?:\D.*)?)$")
P_SINGLE = re.compile(rf"^(?P<a>{_TEAM})\s+{_sc('s')}\s+(?P<b>{_TEAM}){_REST}")
# "FLUMINENSE 1 x BOTAFOGO 1": gols logo depois de cada clube
P_TEAM_GOALS = re.compile(rf"^(?P<a>{_TEAM})\s+(?P<sh>\d{{1,2}})\s+[xX×]\s+(?P<b>{_TEAM})\s+(?P<sa>\d{{1,2}})(?P<rest>)\s*$")
# Três jogos numa linha (Série C 1999): "Moto Clube (MA)   1-1 0-1 1-2 Fluminense (RJ)"
P_THREE_LEG = re.compile(rf"^(?P<a>{_TEAM})\s+{_sc('s')}\s+{_sc('t')}\s+{_sc('u')}\s+(?P<b>{_TEAM}){_REST}")
_WEEKDAY_TAIL = re.compile(r"\s+(?:segunda|ter[cç]a|quarta|quinta|sexta|s[áa]bado|domingo)(?:-feira)?\s*$", re.I)
# Linha de apresentação de participante: "Fluminense FC (Rio de Janeiro, RJ)",
# "FLUMINENSE Futebol Clube (Feira de Santana-BA)"
_INTRO = re.compile(r"^\s*(?:[A-Za-zÀ-ÿ.]+\s+){0,3}?fluminense\b(?:\s+(?:fc|f\.\s?c\.|futebol\s+clube|football\s+club))?"
                    r"\s*\(([^)]*)\)\s*$", re.I)

_PEN = [re.compile(r"\[\s*(?P<who>[^\]\d]+?)\s+(?P<x>\d+)\s*-\s*(?P<y>\d+)\s+on\s+pen", re.I),
        re.compile(r"\((?P<x>\d+)\s*-\s*(?P<y>\d+)\s*p(?:en)?\.?\)", re.I),
        re.compile(r"(?<![\d-])(?P<x>\d+)\s*-\s*(?P<y>\d+)\s*p(?:en)?\b", re.I),
        re.compile(r"\bpen(?:alties|s)?\.?\s*(?P<x>\d+)\s*-\s*(?P<y>\d+)", re.I)]
_VENUE_PLAYED = re.compile(r"\[\s*(?:played|jogo|disputado)\s+(?:in|at|em|no|na)\s+(?P<v>[^\]]+)\]", re.I)
_VENUE_PAREN = re.compile(r"^\s*\((?P<v>[A-Za-zÀ-ÿ][^()\d]{2,80})\)\s*\.?\s*$")
_NOT_PLAYED = re.compile(r"\b(n/?p|w\.?\s?o\.?|walk-?over|awarded|abandoned|annulled|anulad\w*|"
                         r"not played|suspended|interrupted|interrompid\w*)\b", re.I)
_STAGE_WORDS = re.compile(
    r"\b(round|phase|stage|group|grupo|final|finals|semi\w*|quarter\w*|eighth|1/8|1/4|1/2|playoffs?|"
    r"play-offs?|turno|returno|taça|taca|fase|rodada|zone|zona|decision|knockout|octavos|cuartos|"
    r"preliminary|torneio|tournament|liguilla|hexagonal|quadrangular|triangular|league|copa)\b", re.I)


@dataclass
class ParsedMatch:
    date: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    stage: str | None = None
    round: str | None = None
    home_country: str | None = None
    away_country: str | None = None
    home_pens: int | None = None
    away_pens: int | None = None
    stadium: str | None = None
    city: str | None = None
    referee: str | None = None
    venue_country: str | None = None     # país do local, como escrito na página (inglês)
    attendance: int | None = None
    scorers: list[tuple[str, str, int | None, str]] = field(default_factory=list)  # (lado, nome, minuto, tipo)
    line: str = ""
    from_sheet: bool = False              # veio de uma ficha de jogo ("Data –", "Local –", "Árbitro –")


@dataclass
class PageResult:
    matches: list[ParsedMatch] = field(default_factory=list)
    undated: list[str] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)


class _Clock:
    def __init__(self, year: int):
        self.base = year
        self.first_month: int | None = None

    def iso(self, d: int, m: int, y: int | None = None) -> str | None:
        if not (1 <= m <= 12 and 1 <= d <= 31):
            return None
        if y is not None:
            year = y + (1900 if y >= 30 else 2000) if y < 100 else y
        else:
            if self.first_month is None:
                self.first_month = m
            year = self.base + (1 if m < self.first_month - 1 else 0)
        try:
            return date(year, m, d).isoformat()
        except ValueError:
            return None


def _month(tok: str | None) -> int | None:
    return MONTHS.get(tok.lower().rstrip(".")) if tok else None


def _date_parts(m: re.Match) -> tuple[int, int, int | None] | None:
    g = m.groupdict()
    for d, mo, y in (("d1", "m1", "y1"), ("d2", "m2", "y2"), ("d3", "m3", "y3"), ("d4", "m4", "y4")):
        if g.get(d):
            month = int(g[mo]) if mo == "m4" else _month(g[mo])
            if not month:
                return None
            return int(g[d]), month, int(g[y]) if y and g.get(y) else None
    return None


def parse_header_dates(body: str) -> list[tuple[int, int, int | None]] | None:
    """'Aug 24 and 31' -> [(24, 8, None), (31, 8, None)]; None se não for só uma lista de datas."""
    body = (body or "").strip().rstrip(".")
    if not body:
        return None
    sm = re.fullmatch(_D_SLASH_MON, body, re.I)                       # 20/sep/87
    if sm:
        return [(int(sm.group("d1")), _month(sm.group("m1")), int(sm.group("y1")) if sm.group("y1") else None)]
    my = re.fullmatch(rf"({_MON})\s+(\d{{1,2}})\s*/\s*(\d{{2}})", body, re.I)  # Jan 24/87
    if my:
        return [(int(my.group(2)), _month(my.group(1)), int(my.group(3)))]
    if not _ONLY_DATES.match(body):
        return None
    num = re.fullmatch(r"(\d{1,2})\s*[./]\s*(\d{1,2})(?:\s*[./]\s*(\d{2,4}))?", body)
    if num:
        y = int(num.group(3)) if num.group(3) else None
        return [(int(num.group(1)), int(num.group(2)), y)]
    year_m = re.search(r"\b(1[89]\d\d|20\d\d)\b", body)
    year = int(year_m.group(1)) if year_m else None
    body = re.sub(r",?\s*\b(1[89]\d\d|20\d\d)\b", "", body)
    out: list[tuple[int, int, int | None]] = []
    month: int | None = None
    # "Aug 24 and 31", "Apr 30-May 6" (ida e volta): cada item é a data de um jogo.
    for part in re.split(r"\s*(?:\band\b|\be\b|&|,|/|-|–)\s*", body, flags=re.I):
        if not part:
            continue
        mm = _MON_RX.search(part)
        if mm:
            month = _month(mm.group(0))
        dd = re.search(r"\d{1,2}", part)
        if not dd or month is None:
            return None
        out.append((int(dd.group(0)), month, year))
    return out or None


_TITLE_SHORT = {"SAO", "SÃO", "DE", "DA", "DO", "DOS", "DAS", "RIO", "ITA", "UNI"}


def _clean_team(s: str) -> str:
    s = re.sub(r"\s{2,}", " ", s).strip(" .:-–")
    if s.isupper() and len(s) > 3:          # fichas em caixa alta: "FLUMINENSE", "S. C. AMERICANO"
        # Siglas curtas ("URT", "CSA") e UF entre parênteses ("(MG)") ficam como estão.
        s = re.sub(r"(?<![\wÀ-ÿ(])([A-ZÀ-Ý])([A-ZÀ-Ý]+)",
                   lambda m: m.group(0) if (len(m.group(0)) <= 3 and m.group(0) not in _TITLE_SHORT)
                   else m.group(1) + m.group(2).lower(), s)
    return s


def _penalties(rest: str, a: str) -> tuple[int, int] | None:
    """Pênaltis do ponto de vista do clube `a` (primeiro da linha)."""
    for rx in _PEN:
        m = rx.search(rest or "")
        if m:
            x, y = int(m.group("x")), int(m.group("y"))
            who = (m.groupdict().get("who") or "").strip()
            if who and split_name(who)[0] != split_name(a)[0]:
                x, y = y, x
            return x, y
    return None


_MINUTE = re.compile(r"(?<![\w+])(?P<min>\d{1,3})\s*['’]?(?:\s*\+\s*\d{1,2}\s*['’]?)?\s*(?:pen|pk|p|og|o/g)?(?![\w])",
                     re.I)


def parse_scorers(text: str) -> list[list[tuple[str, int | None, str]]]:
    """'[Assis, Vica; Lima]' -> [[('Assis', None, 'gol'), ('Vica', None, 'gol')], [('Lima', None, 'gol')]].

    Retorna [] se algum trecho não for entendido (melhor nenhum autor do que autor errado).
    """
    text = text.strip()
    text = text[1:-1] if text[:1] in "[(" and text[-1:] in "])" else text
    text = text.replace("’", "'")
    sides: list[list[tuple[str, int | None, str]]] = []
    for part in text.split(";"):
        goals: list[tuple[str, int | None, str]] = []
        last_name: str | None = None
        for tok in [t.strip() for t in part.split(",") if t.strip()]:
            kind = "gol"
            if re.search(r"(o/g|\bog\b|\d\s*og\b|own goal|contra)", tok, re.I):
                kind = "gol_contra"
            elif re.search(r"(\bpen\b|\bpk\b|\d\s*pen\b|\d\s*p\b|pênalti|penalti)", tok, re.I):
                kind = "gol_penalti"
            mult = re.search(r"\(\s*(\d)\s*\)", tok)
            body = re.sub(r"\(\s*\d\s*\)", "", tok)
            minutes = [int(m.group("min")) for m in _MINUTE.finditer(body)]
            name = _MINUTE.sub("", body)
            name = re.sub(r"(o/g|\bog\b|own goal|contra|\bpen\b|\bpk\b|pênalti|penalti)", "", name, flags=re.I)
            name = re.sub(r"\(\s*\)", "", name)
            name = re.sub(r"\s+", " ", name).strip(" -'.")
            if not name and last_name and minutes:           # "Thiago Neves 22, 55": 55 é outro gol dele
                name = last_name
            if not name or not re.search(r"[A-Za-zÀ-ÿ]{2}", name) or len(name) > 40:
                return []
            last_name = name
            if minutes:
                goals.extend((name, mn, kind) for mn in minutes)
            else:
                goals.extend((name, None, kind) for _ in range(int(mult.group(1)) if mult else 1))
        sides.append(goals)
    return sides


def _attach_scorers(pm: ParsedMatch, text: str) -> None:
    sides = parse_scorers(text)
    if not sides:
        return
    if len(sides) == 1:                       # só um lado marcou
        if pm.home_goals and not pm.away_goals:
            sides = [sides[0], []]
        elif pm.away_goals and not pm.home_goals:
            sides = [[], sides[0]]
        else:
            return
    if len(sides) != 2:
        return
    for side, goals, total in (("home", sides[0], pm.home_goals), ("away", sides[1], pm.away_goals)):
        if len(goals) == total:               # só grava se a contagem bate com o placar
            pm.scorers.extend((side, n, mn, k) for n, mn, k in goals)


_BLOCK = re.compile(r"[\[(](?:[^\[\]()]|\([^()]*\))*[\])]")


_QUALIFIED_HOME = re.compile(r"^([^\d\[\]()]+?\s*\([A-Za-zÀ-ÿ][^()\d]{1,40}\))\s+\d{1,2}\s?[-x]\s?\d{1,2}")


_CELL_DATE = re.compile(r"^\d{1,2}/\d{1,2}(?:/\d{2,4})?$")
_CELL_MATCH = re.compile(r"^[A-ZÀ-Ý].*?(?:\d{1,2}\s?[-xX×]\s?\d{1,2}|\sawd\s)")


def _cell(x: str) -> bool:
    return bool(_CELL_DATE.match(x) or _CELL_MATCH.match(x))


def _split_columns(text: str) -> str:
    """Páginas com jogos em duas colunas ("Náutico 2x0 Unibol          Fluminense 0x1 Sergipe"):
    cada bloco de duas colunas é reescrito como a coluna da esquerda seguida da coluna da direita."""
    lines = text.split("\n")

    def right_col(ln: str) -> int | None:
        for m in re.finditer(r"\s{2,}(?=\S)", ln):
            p = m.end()
            if p >= 30 and _cell(ln[p:].strip()) and (not ln[:p].strip() or _cell(ln[:p].strip())):
                return p
        return None

    out: list[str] = []
    i = 0
    while i < len(lines):
        col = right_col(lines[i])
        if col is None:
            out.append(lines[i])
            i += 1
            continue
        j, n2 = i, 0
        while j < len(lines):                      # estende o bloco enquanto as linhas cabem nas colunas
            ln = lines[j].rstrip()
            c = right_col(ln)
            if c is not None:
                n2 += 1
            elif ln and not (ln[:col - 1].strip() == "" or (len(ln) <= col - 1 and _cell(ln.strip()))):
                break
            j += 1
        if n2 < 3:
            out.append(lines[i])
            i += 1
            continue
        block = lines[i:j]
        out += [ln[:col - 1].rstrip() for ln in block if ln[:col - 1].strip()]
        out += [ln[col - 1:].strip() for ln in block if ln[col - 1:].strip()]
        i = j
    return "\n".join(out)


_SHEET_ANY = re.compile(r"^(?:Data|Local|[ÁA]rbitro|Renda|P[úu]blico)\s*[–:-]", re.I)
_SHEET_DATE_W = re.compile(r"^Data\s*[–:-]\s*(\d{1,2})º?\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})\b", re.I)


def _sheet_info(lines: list[str], idx: int, clock: _Clock) -> dict | None:
    """Se a linha `idx` é o cabeçalho de uma ficha de jogo (seguida, em até 3 linhas, de "Data –",
    "Local –" ou "Árbitro –"), devolve {date, stadium, city, referee}; senão None."""
    nxt = [ln.strip() for ln in lines[idx + 1: idx + 14] if ln.strip()][:8]
    if not any(_SHEET_ANY.match(ln) for ln in nxt[:3]):
        return None
    info: dict = {}
    for ln in nxt:
        if not _SHEET_ANY.match(ln) and (P_SINGLE.match(ln) or P_TEAM_GOALS.match(ln)):
            break                                         # começou outro jogo
        dm, dw = _SHEET_DATE.match(ln), _SHEET_DATE_W.match(ln)
        if dm and "date" not in info:
            info["date"] = clock.iso(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
        elif dw and "date" not in info and _month(dw.group(2)):
            info["date"] = clock.iso(int(dw.group(1)), _month(dw.group(2)), int(dw.group(3)))
        elif (pl := _SHEET_PLACE.match(ln)) and "stadium" not in info:
            place = pl.group("v").strip(" .–-")
            paren = (pl.group("city") or "").strip(" .–-")
            parts = [p.strip() for p in place.split(",") if p.strip()]
            info["stadium"] = parts[0] if parts else None
            city = ", ".join(parts[1:]) if len(parts) > 1 else (paren if not re.fullmatch(r"[A-Z]{2}", paren) else "")
            info["city"] = city or None
        elif (rf := _SHEET_REF.match(ln)) and "referee" not in info:
            info["referee"] = rf.group("r").strip() or None
    return info


def _ours_place(p: str) -> bool:
    return bool(re.search(r"(?i)rio de janeiro|\b(?:RJ|GB)\b", p))       # GB: Guanabara (1960-1975)


def parse_page(text: str, year: int, default_state: str | None = None,
               national: bool | None = None) -> PageResult:
    """`national`: página de competição nacional brasileira (onde homônimos do Fluminense
    aparecem com sufixo de estado). Padrão: True quando não há `default_state`."""
    res = PageResult()
    clock = _Clock(year)
    national = (default_state is None) if national is None else national
    # Outros clubes chamados Fluminense (Feira de Santana-BA, Nova Friburgo-RJ, Teresina-PI...).
    # Nas páginas da RSSSF eles aparecem qualificados ("Fluminense-BA", "Fluminense (Nova Friburgo)");
    # "Fluminense" sozinho é o do Rio. Nas páginas do Brasileiro, as seções de outras divisões já foram
    # descartadas (rsssf.flu_division), o que afasta o homônimo quando a página não o qualifica.
    text = _split_columns(text)
    # Página que apresenta um homônimo como participante ("Fluminense FC (Feira de Santana, BA)") e depois
    # o chama só de "Fluminense": o dono de cada "Fluminense" é o da última apresentação (grupo a grupo).
    homonym_intro = national and any((im := _INTRO.match(ln)) and not _ours_place(im.group(1))
                                     for ln in text.split("\n"))
    owner: str | None = None
    # Nomes com qualificador entre parênteses usados como MANDANTE ("Fluminense (Nova Friburgo) 0-0 X"):
    # quando o mesmo "(…)" vem depois do visitante, é parte do nome, não o local do jogo.
    qualified: set[str] = set()
    for ln in text.split("\n"):
        b0 = ln.strip()
        lm0 = _LEADING_DATE.match(b0)
        if lm0:
            b0 = b0[lm0.end():].strip()
        qm0 = _QUALIFIED_HOME.match(b0)
        if qm0:
            qualified.add(norm(qm0.group(1)))
    ctx_dates: list[tuple[int, int, int | None]] = []
    stage: str | None = None
    rnd: str | None = None
    pending: list[ParsedMatch] = []
    scorer_buf: list[str] = []
    detail: dict | None = None               # "First leg [data, estádio, cidade, país, att, ref]" -> próximo jogo
    lines = text.split("\n")

    def bare(name: str) -> bool:
        return bool(re.fullmatch(r"\s*Fluminense\s*", name, re.I))

    def flu(name: str) -> bool:
        # Homônimos qualificados ("Fluminense-BA", "Fluminense (BA)") não tornam ambíguo o "Fluminense"
        # sem qualificação: nas páginas da RSSSF esse é o do Rio. Exceção: páginas com apresentação
        # do homônimo (ver `owner`).
        if bare(name):
            if owner:
                return owner == "ours"
            return not homonym_intro
        return is_fluminense(name, default_state)

    def flush() -> None:
        nonlocal scorer_buf, pending
        if scorer_buf and pending:
            blocks = _BLOCK.findall(" ".join(scorer_buf))
            targets = [p for p in pending if p.home_goals + p.away_goals > 0]
            if len(blocks) == len(targets):
                for pm, blk in zip(targets, blocks):
                    _attach_scorers(pm, blk)
        scorer_buf, pending = [], []

    def add(pm: ParsedMatch, raw: str) -> None:
        pm.home = "Fluminense" if flu(pm.home) else pm.home
        pm.away = "Fluminense" if flu(pm.away) else pm.away
        pm.stage, pm.round, pm.line = stage, rnd, raw.strip()
        res.matches.append(pm)
        pending.append(pm)

    def conv_cc(cc: str | None) -> str | None:
        return FIFA_ISO2.get((cc or "").upper())

    for idx, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        # ----- autores de gols logo após um jogo do Fluminense
        open_buf = scorer_buf and " ".join(scorer_buf).count("[") + " ".join(scorer_buf).count("(") > \
            " ".join(scorer_buf).count("]") + " ".join(scorer_buf).count(")")
        if pending and (open_buf or (s[:1] in "[(" and not _VENUE_PLAYED.match(s)
                                      and not parse_header_dates((_HEADER.match(s) or re.match("", "")).groupdict().get("body", "")))):
            scorer_buf.append(s)
            continue
        flush()

        if national:
            im = _INTRO.match(s)
            if im:
                owner = "ours" if _ours_place(im.group(1)) else "other"
                continue
            if re.match(r"(?i)^(group|grupo|participa)", s):
                owner = None
            elif re.search(r"Fluminense\s*(?:\(\s*RJ\s*\)|-RJ\b|\(\s*Rio de Janeiro)", s):
                owner = "ours"

        # ----- linhas de ficha de jogo ("Data –", "Local –", "Árbitro –"): lidas por _sheet_info
        if _SHEET_ANY.match(s):
            continue

        dm2 = _DETAIL.match(s)
        if dm2:
            d_parts = parse_header_dates(dm2.group("date"))
            fields = [f.strip() for f in dm2.group("body").split(",")]
            info: dict = {"date": clock.iso(*d_parts[0]) if d_parts else None}
            place = []
            for f in fields:
                if re.match(r"(?i)att\b|attendance", f):
                    n = re.sub(r"\D", "", f)
                    info["attendance"] = int(n) if n else None
                elif re.match(r"(?i)ref\b|referee", f):
                    info["referee"] = re.sub(r"(?i)^ref(?:eree)?\s*:?\s*", "", f).split("(")[0].strip() or None
                elif f and not info.get("referee"):
                    place.append(f)
            if place:
                info["stadium"] = place[0]
                info["city"] = place[1] if len(place) > 1 else None
                info["venue_country"] = place[2] if len(place) > 2 else None
            detail = info if info["date"] else None
            continue

        sd = _WEEKDAY_TAIL.sub("", s)                 # "24/10/95        TERCA"
        hm = _HEADER.match(sd)
        if hm and (sd[:1] in "[(" or _NUM_DATE_LINE.fullmatch(sd) or re.fullmatch(_D_SLASH_MON, sd, re.I)
                   or re.fullmatch(rf"{_MON}\s+\d{{1,2}}(?:,?\s+\d{{4}})?", sd, re.I)):
            dates = parse_header_dates(hm.group("body"))
            if dates:
                ctx_dates = dates
                continue
        rm = re.match(r"^(?:Round|Rodada|Matchday|Jornada|Fecha)\s*:?\s*(\d+)\b(?P<tail>.*)$", s, re.I) or \
            re.match(r"^(\d+)(?:ª|a|st|nd|rd|th)?\s*(?:Round|Rodada)\b(?P<tail>.*)$", s, re.I)
        lg = re.match(r"(?i)^(?:first|second|1st|2nd)\s+legs?\s*[\[(]([^\])]+)[\])]\s*$", s)
        if lg and (lg_dates := parse_header_dates(lg.group(1))):
            ctx_dates = lg_dates                       # "First Legs [Aug 24]"
            continue
        if rm and not re.search(r"\d+\s?-\s?\d+", rm.group("tail")):
            rnd = rm.group(1)
            ctx_dates = []
            tail = re.search(r"[\[(]([^\])]+)[\])]", rm.group("tail"))
            if tail:
                ctx_dates = parse_header_dates(tail.group(1)) or []
            continue
        if (not re.search(r"\d+\s?[-x]\s?\d+|\d+\s+a\s+\d+", s) and len(s) <= 70 and _STAGE_WORDS.search(s)
                and not s[:1].islower() and not re.search(r"[.!?]\s+\S|\.$", s)
                and not re.search(r"(?i)\b(played|retired|qualified|wins?|won|considering|topscorers?|"
                                  r"colocação|table|tabela|classifica\w*)\b", s)
                and s[:1] not in "[(" and not re.search(r"\b(1[89]\d\d|20\d\d)\b", s)
                and ";" not in s and s.count(",") <= 1
                and not re.match(r"(?i)(gols?|obs|fonte|source|local|data|[áa]rbitro|renda|p[úu]blico|nb|note|"
                                 r"expuls|cart|escala|t[ée]cnico)\b", s)):
            stage = re.sub(r"\s+", " ", re.sub(r"\s*[\[(].*$|\s*\*.*$", "", s.lstrip("* "))).strip(" :") or stage
            rnd = None
            ctx_dates = []
            tail = re.search(r"[\[(]([^\])]+)[\])]", s)
            if tail:
                ctx_dates = parse_header_dates(tail.group(1)) or []
            continue

        # ----- data no início da linha
        # Continuação de nota em coluna à direita ("Fluminense 2-2 Flamengo      the player Rubens..."):
        # o texto depois de um espaço largo que começa em minúscula não é parte da linha do jogo.
        body = re.split(r"\s{4,}(?=[a-z\"'])", s)[0]
        line_date: str | None = None
        lm = _LEADING_DATE.match(body)
        if lm and (parts := _date_parts(lm)):
            line_date = clock.iso(*parts)
            body = body[lm.end():].strip()
        elif national and (cd := re.match(r"^(\d{2})(\d{2})\s{2,}(?=[A-ZÀ-Ý])", body)) and \
                (iso4 := clock.iso(int(cd.group(1)), int(cd.group(2)))):
            line_date, body = iso4, body[cd.end():]                # "2408  BAHIA 0x1 FLUMINENSE" (ddmm)
        elif re.match(r"^\d{1,3}\s+(?=[A-ZÀ-Ý])", body):
            body = re.sub(r"^\d{1,3}\s+", "", body)        # número do confronto (Copa do Brasil)

        def ctx(i: int) -> str | None:
            return clock.iso(*ctx_dates[i]) if len(ctx_dates) > i else None

        # ----- ida e volta com data de cada jogo
        m = P_TWO_LEG_DATED.match(body)
        if m:
            a, b = _clean_team(m.group("a")), _clean_team(m.group("b"))
            if flu(a) or flu(b):
                for leg, (tag, dkey, np) in enumerate((("s", "dt1", "np1"), ("t", "dt2", "np2"))):
                    if m.group(np) or m.group(f"{tag}h") is None:
                        res.ambiguous.append(s)
                        continue
                    dd = parse_header_dates(m.group(dkey))
                    iso = clock.iso(*dd[0]) if dd and len(dd) == 1 else None
                    if not iso:
                        res.undated.append(s)
                        continue
                    x, y = int(m.group(f"{tag}h")), int(m.group(f"{tag}a"))
                    pm = ParsedMatch(iso, a, b, x, y) if leg == 0 else ParsedMatch(iso, b, a, y, x)
                    if leg == 1 and (pens := _penalties(m.group("rest"), a)):
                        pm.home_pens, pm.away_pens = pens[1], pens[0]
                    add(pm, s)
            continue

        # ----- formato com código de país (Sul-Americana)
        m = None
        for rx, two in ((P_TWO_LEG_CC, True), (P_ONE_LEG_CC, False)):
            mm = rx.match(body)
            if mm and conv_cc(mm.group("ca")) and conv_cc(mm.group("cb")):
                m = mm
                break
        if m:
            a, b = _clean_team(m.group("a")), _clean_team(m.group("b"))
            ca, cb = conv_cc(m.group("ca")), conv_cc(m.group("cb"))
            if (ca == "BR" and flu(a)) or (cb == "BR" and flu(b)):
                n_legs = 2 if two else 1
                dates = [line_date] if (line_date and n_legs == 1) else \
                    [ctx(i) for i in range(n_legs)] if len(ctx_dates) == n_legs else [None] * n_legs
                for leg in range(n_legs):
                    if dates[leg] is None:
                        res.undated.append(s)
                        continue
                    tag = "s" if leg == 0 else "t"
                    x, y = int(m.group(f"{tag}h")), int(m.group(f"{tag}a"))
                    if leg == 0:
                        pm = ParsedMatch(dates[0], a, b, x, y, home_country=ca, away_country=cb)
                    else:
                        pm = ParsedMatch(dates[1], b, a, y, x, home_country=cb, away_country=ca)
                        if pens := _penalties(m.group("rest"), a):
                            pm.home_pens, pm.away_pens = pens[1], pens[0]
                    add(pm, s)
            continue

        # ----- três jogos numa linha (1º no campo do 1º clube; 2º e 3º no do 2º, conforme nota da página)
        m = P_THREE_LEG.match(body)
        if m:
            a, b = _clean_team(m.group("a")), _clean_team(m.group("b"))
            if flu(a) or flu(b):
                rest = m.group("rest") or ""
                dates = [ctx(i) for i in range(3)] if len(ctx_dates) == 3 else []
                fl = re.search(rf"1st leg\s+({_MON}\s+\d{{1,2}})", rest, re.I)
                if dates and fl and (d1 := parse_header_dates(fl.group(1))):
                    dates[0] = clock.iso(*d1[0])
                convention = re.search(r"(?i)home\s+2nd\s*\(?\s*and\s+3rd", text)
                if len(dates) != 3 or not all(dates) or not convention:
                    res.undated.append(s)
                    continue
                for i, tag in enumerate(("s", "t", "u")):
                    x, y = int(m.group(f"{tag}h")), int(m.group(f"{tag}a"))     # do ponto de vista de `a`
                    pm = ParsedMatch(dates[i], a, b, x, y) if i == 0 else ParsedMatch(dates[i], b, a, y, x)
                    cm = re.search(rf"(?i)\b{('1st', '2nd', '3rd')[i]}\s+(?:match|leg|game)\s+in\s+([^,\]\[]+)", rest)
                    if cm:
                        pm.city = cm.group(1).strip()
                    add(pm, s)
            continue

        # ----- ida e volta numa linha, datas no cabeçalho
        m = P_TWO_LEG.match(body)
        if m:
            a, b = _clean_team(m.group("a")), _clean_team(m.group("b"))
            if flu(a) or flu(b):
                if len(ctx_dates) == 2 and not line_date:
                    pm1 = ParsedMatch(ctx(0), a, b, int(m.group("sh")), int(m.group("sa")))
                    pm2 = ParsedMatch(ctx(1), b, a, int(m.group("ta")), int(m.group("th")))
                    if pens := _penalties(m.group("rest"), a):
                        pm2.home_pens, pm2.away_pens = pens[1], pens[0]
                    if pm1.date and pm2.date:
                        add(pm1, s)
                        add(pm2, s)
                        continue
                res.undated.append(s)
            continue

        # ----- jogo simples
        m = P_DASH.match(body) or P_SINGLE.match(body) or P_TEAM_GOALS.match(body)
        if m:
            a, b = _clean_team(m.group("a")), _clean_team(m.group("b"))
            rest = m.group("rest") or ""
            qm = re.match(r"\s*(\([^()]+\))\s*(.*)$", rest)
            if qm and norm(f"{b} {qm.group(1)}") in qualified:
                b, rest = f"{b} {qm.group(1)}", qm.group(2)
            det, detail = detail, None
            if det and not line_date:
                line_date = det["date"]
            dd = re.match(r"\s*\((\d{1,2})/(\d{1,2})\)\s*(.*)$", rest)    # Copa do Brasil: "2-5 (15/02)"
            if dd and not line_date:
                line_date, rest = clock.iso(int(dd.group(1)), int(dd.group(2))), dd.group(3)
            own = re.match(rf"\s*\[\s*({_MON}\s+\d{{1,2}})\s*\]\s*$", rest, re.I)   # "2-0 Fluminense  [Sep 11]"
            if own and not line_date and (od := parse_header_dates(own.group(1))):
                line_date, rest = clock.iso(*od[0]), ""
            if not (flu(a) or flu(b)):
                if owner is None and homonym_intro and (bare(a) or bare(b)):
                    res.ambiguous.append(s)
                continue
            if _NOT_PLAYED.search(rest):
                res.ambiguous.append(s)
                continue
            sheet = _sheet_info(lines, idx, clock)
            if sheet is not None:
                # Ficha de jogo: a data vem da linha "Data", nunca do cabeçalho da rodada.
                if not sheet.get("date"):
                    res.undated.append(s)
                    continue
                pm = ParsedMatch(sheet["date"], a, b, int(m.group("sh")), int(m.group("sa")),
                                 stadium=sheet.get("stadium"), city=sheet.get("city"),
                                 referee=sheet.get("referee"), from_sheet=True)
                add(pm, s)
                continue
            iso = line_date or (ctx(0) if len(ctx_dates) == 1 else None)
            if iso is None:
                res.undated.append(s)
                continue
            pm = ParsedMatch(iso, a, b, int(m.group("sh")), int(m.group("sa")))
            if pens := _penalties(rest, a):
                pm.home_pens, pm.away_pens = pens
            vm = _VENUE_PLAYED.search(rest)
            vp = None if vm else _VENUE_PAREN.match(rest.lstrip(" -–"))
            venue = vm.group("v") if vm else vp.group("v") if vp else None
            if venue:
                parts = [p.strip() for p in venue.split(",") if p.strip()]
                pm.stadium = parts[0] if parts else None
                if len(parts) > 1:
                    pm.city = re.sub(r"\s*-\s*[A-Z]{2}$", "", parts[-1]).strip() or None
            if det:
                for k in ("stadium", "city", "venue_country", "attendance", "referee"):
                    if det.get(k):
                        setattr(pm, k, det[k])
            add(pm, s)
            continue

        if re.search(r"(?i)fluminense", s) and re.search(r"\d+\s?[-x]\s?\d+", s) and not re.match(r"^\s*\d+\s*[.)-]", s):
            res.unparsed.append(s)
    flush()
    return res
