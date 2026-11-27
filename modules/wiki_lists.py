"""Leitura das listas da Wikipédia (pt) salvas em data/reference/wikipedia/.

Cada arquivo .wiki é uma cópia fiel do wikitexto de um artigo, acompanhada de um .json com o
título e o número da revisão (revid) — é isso que permite citar exatamente a versão usada.
Nada aqui é inventado: o que não for encontrado no texto fica como None ("—" na tela).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

from core.text import norm as normalize

WIKI_DIR = Path(__file__).resolve().parent.parent / "data" / "reference" / "wikipedia"
PT_MONTHS = {m: i for i, m in enumerate(
    ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
     "outubro", "novembro", "dezembro"], start=1)}


# ----------------------------------------------------------------------------- utilidades
def _read(name: str) -> str:
    p = WIKI_DIR / f"{name}.wiki"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def source(name: str) -> dict:
    """{'title', 'revid', 'url'} da cópia usada (para citação)."""
    p = WIKI_DIR / f"{name}.json"
    meta = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    title = meta.get("title", "")
    rev = meta.get("revid")
    url = (f"https://pt.wikipedia.org/w/index.php?title={title.replace(' ', '_')}&oldid={rev}"
           if title and rev else "")
    return {"title": title, "revid": rev, "url": url}


def _strip(cell: str) -> str:
    """Wikitexto → texto simples (remove refs, notas, predefinições, formatação)."""
    s = re.sub(r"<ref[^>]*/>", "", cell)
    s = re.sub(r"<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref.*$", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:Imagem|Ficheiro|File|Image):[^\]]*\]\]", "", s, flags=re.I)
    for _ in range(3):
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()


def _link(cell: str) -> tuple[str | None, str]:
    """Primeiro [[alvo|texto]] da célula → (alvo, texto)."""
    m = re.search(r"\[\[(?!Imagem:|Ficheiro:|File:)([^|\]]+)(?:\|([^\]]+))?\]\]", cell)
    if not m:
        return None, _strip(cell)
    return m.group(1).strip(), (m.group(2) or m.group(1)).strip()


def _rows(text: str) -> list[list[str]]:
    """Divide uma tabela wiki em linhas de células (aceita '||' e '!!' na mesma linha)."""
    rows: list[list[str]] = []
    for chunk in re.split(r"\n\|-[^\n]*", text):
        cells: list[str] = []
        for line in chunk.split("\n"):
            line = line.rstrip()
            if line.startswith(("{|", "|}", "|+")):
                continue
            if line.startswith(("|", "!")):
                for c in re.split(r"\|\||!!", line[1:]):
                    # remove atributos 'style="..." |' do início da célula
                    if re.match(r'^\s*(?:[a-z-]+\s*=\s*"[^"]*"\s*)+\|(?!\|)', c):
                        c = c.split("|", 1)[1]
                    cells.append(c.strip())
            elif cells and line.strip():
                cells[-1] += "\n" + line          # continuação da célula anterior
        if cells:
            rows.append(cells)
    return rows


def _section(text: str, title: str) -> str:
    m = re.search(r"^=+\s*" + re.escape(title) + r"\s*=+\s*$", text, flags=re.M)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^==[^=]", rest, flags=re.M)
    return rest[: nxt.start()] if nxt else rest


def _pt_date(s: str) -> date | None:
    m = re.search(r"(\d{1,2})º?\s+de\s+([a-zç]+)\s+de\s+(\d{4})", s.lower())
    if m and m.group(2) in PT_MONTHS:
        return date(int(m.group(3)), PT_MONTHS[m.group(2)], int(m.group(1)))
    return None


def _br_date(s: str) -> date | None:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s)
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        return None


# ----------------------------------------------------------------------------- presidentes
@dataclass
class Presidency:
    order: int
    name: str
    link: str | None
    start: date | None
    end: date | None            # None = mandato em curso


@lru_cache(maxsize=1)
def presidents() -> list[Presidency]:
    text = _section(_read("presidentes"), "Lista de presidentes")
    out: list[Presidency] = []
    for cells in _rows(text):
        joined = " || ".join(cells)
        dates = re.findall(r"\d{1,2}º? de [a-zç]+ de \d{4}", joined.lower())
        if not dates:
            continue
        name_cell = cells[-1]
        link, name = _link(name_cell)
        name = _strip(name) if link else _strip(name_cell)
        current = "atualmente" in joined.lower()
        start = _pt_date(dates[0])
        end = None if current else _pt_date(dates[-1])
        out.append(Presidency(len(out) + 1, name, link, start, end))
    return out


# ----------------------------------------------------------------------------- técnicos
@dataclass
class CoachSpell:
    order: int
    name: str
    link: str | None
    start: date | None
    end: date | None
    interim: bool
    highlights: str
    wiki_record: dict | None = None     # J/V/E/D/% da tabela "Estatísticas" (carreira inteira no clube)


@lru_cache(maxsize=1)
def coach_records() -> dict[str, dict]:
    """Tabela 'Estatísticas' da lista de treinadores: nome → {J, V, E, D, pct, interim}."""
    text = _section(_read("treinadores"), "Estatísticas")
    out: dict[str, dict] = {}
    for cells in _rows(text):
        if len(cells) < 6:
            continue
        name = _strip(cells[0])
        nums = [c.replace(".", "").replace(",", ".").strip() for c in cells[1:6]]
        try:
            j, v, e, d = (int(x) for x in nums[:4])
            pct = float(nums[4])
        except ValueError:
            continue
        out[normalize(name)] = {"name": name, "J": j, "V": v, "E": e, "D": d, "pct": pct,
                                "interim": "lightgreen" in " ".join(cells[:1]) or False}
    return out


@lru_cache(maxsize=1)
def coaches() -> list[CoachSpell]:
    raw = _read("treinadores")
    text = _section(raw, "Ordem cronológica")
    recs = coach_records()
    out: list[CoachSpell] = []
    for chunk in re.split(r"\n(?=\|-)", text):
        header, _, body = chunk.partition("\n")
        if not header.startswith("|-"):
            continue
        cells = _rows("\n" + body)
        if not cells:
            continue
        cells = [c for c in cells[0] if c != ""] or cells[0]
        if len(cells) < 2:
            continue
        period = cells[1]
        start = _br_date(period)
        if not start:
            continue
        ds = re.findall(r"\d{2}/\d{2}/\d{4}", period)
        if len(ds) > 1:
            end = _br_date(ds[1])
        elif "–" in period or "-" in period.replace(ds[0], ""):
            end = None                      # "dd/mm/aaaa –" = ainda no cargo
        else:
            end = start                     # data única = passagem de um dia
        link, name = _link(cells[0])
        name = _strip(name if link else cells[0])
        hl = _strip(cells[2]) if len(cells) > 2 else ""
        rec = recs.get(normalize(name))
        out.append(CoachSpell(len(out) + 1, name, link, start, end, "lightgreen" in header, hl, rec))
    return out


# ----------------------------------------------------------------------------- títulos
@dataclass
class TitleGroup:
    category: str
    name: str
    count: int
    years: list[int] = field(default_factory=list)


@lru_cache(maxsize=1)
def main_titles() -> list[TitleGroup]:
    """Tabelas 'Principais títulos' (honrarias, internacionais … estaduais, total)."""
    raw = _read("titulos")
    m = re.search(r"=== Principais títulos ===(.*?)\n==", raw, flags=re.S)
    text = m.group(1) if m else ""
    out: list[TitleGroup] = []
    category = ""
    for cells in _rows(text):
        head = _strip(cells[0]) if len(cells) == 1 else ""
        if head and head.isupper():
            category = head.title()
            continue
        if len(cells) < 4:
            continue
        name = _strip(cells[1])
        count_txt = _strip(cells[2])
        if not count_txt.isdigit() or not name:
            continue
        years_txt = re.sub(r"<sup>.*?</sup>", "", cells[3])
        years_txt = re.sub(r"<ref.*?(</ref>|/>)", "", years_txt, flags=re.S)
        years_txt = re.sub(r"\{\{Nre\|.*", "", years_txt, flags=re.S)
        years = sorted({int(y) for y in re.findall(r"(?<![\d–-])(1[89]\d\d|20\d\d)(?![\d–-])",
                                                    _strip(years_txt))})
        name = re.sub(r"\(\d\)", "", name).strip()
        out.append(TitleGroup(category, name, int(count_txt), years))
    return out


# ----------------------------------------------------------------------------- ídolos e recordes
@dataclass
class Idol:
    rank: int
    name: str
    link: str
    games: int | None
    goals: int | None
    photo: str | None = None
    position: str | None = None
    years: str | None = None
    games_src: str | None = None      # "recordes" (ranking do clube) | "artigo" (caixa do jogador)
    goals_src: str | None = None
    partial: bool = False
    article: str | None = None
    revid: int | None = None


def _ranking(section: str) -> list[tuple[str | None, str, int]]:
    text = _section(_read("recordes"), section)
    m = re.search(r"\{\|.*?\n\|\}", text, flags=re.S)   # só a primeira tabela (ranking geral)
    text = m.group(0) if m else ""
    out = []
    for cells in _rows(text):
        if len(cells) < 3 or not re.match(r"\d+º", _strip(cells[0])):
            continue
        link, disp = _link(cells[1])
        m = re.search(r"\d+", _strip(cells[2]).replace(".", ""))
        if m:
            out.append((link, _strip(disp), int(m.group())))
    return out


@lru_cache(maxsize=1)
def appearances() -> list[tuple[str | None, str, int]]:
    return _ranking("Jogadores que mais atuaram")


@lru_cache(maxsize=1)
def scorers() -> list[tuple[str | None, str, int]]:
    return _ranking("Maiores artilheiros")


def _lookup(table, link: str, display: str) -> int | None:
    base = normalize(re.sub(r"\s*\(.*?\)", "", display))
    for lk, disp, n in table:
        if lk and normalize(lk) == normalize(link):
            return n
    for lk, disp, n in table:
        if normalize(disp) == base:
            return n
    return None


_FLU = re.compile(r"Futebol Fluminense\s*\}\}|\[\[Fluminense Football Club", re.I)


def _num(s: str) -> int | None:
    s = re.sub(r"\{\{0\|[^}]*\}\}", "", s)          # {{0|00}} é só alinhamento
    s = re.sub(r"<ref.*?(</ref>|/>)", "", s, flags=re.S)
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def infobox_flu_stats(wikitext: str) -> dict:
    """Jogos/gols pelo Fluminense na caixa de informações do artigo de um jogador.

    Aceita os dois formatos usados na Wikipédia em português:
    clubeN/jogosN/golsN (Info/Futebol) e clubes + jogos(golos) separados por <br>.
    Soma as passagens; 'partial' indica passagem pelo clube sem número informado.
    """
    games = goals = 0
    found = partial = False
    years: list[str] = []
    fields = dict(re.findall(r"^\s*\|\s*([^=|\n]+?)\s*=\s*(.*)$", wikitext, flags=re.M))
    for k, v in fields.items():
        m = re.fullmatch(r"clube(\d+)", k)
        if m and _FLU.search(v):
            n = m.group(1)
            g, gl = _num(fields.get(f"jogos{n}", "")), _num(fields.get(f"gols{n}", ""))
            years.append(_strip(fields.get(f"ano{n}", "")))
            found = True
            if g is None:
                partial = True
            else:
                games += g
                goals += gl or 0
    if not found and "clubes" in fields:
        clubs = re.split(r"<br\s*/?>", fields["clubes"])
        stats = re.split(r"<br\s*/?>", fields.get("jogos(golos)", fields.get("jogos (golos)", "")))
        for i, c in enumerate(clubs):
            if not _FLU.search(c):
                continue
            found = True
            yl = re.split(r"<br\s*/?>", fields.get("ano") or fields.get("anos") or "")
            years.append(_strip(yl[i]) if i < len(yl) else "")
            cell = stats[i] if i < len(stats) else ""
            cell = re.sub(r"\{\{0\|[^}]*\}\}", "", cell)
            mm = re.search(r"(\d+)\s*\((\d+)\)", cell)
            if mm:
                games += int(mm.group(1))
                goals += int(mm.group(2))
            else:
                partial = True
    pos = next((v for k, v in fields.items() if normalize(k) == "posicao"), "")
    extra = {"years": ", ".join(y for y in years if y) or None,
             "position": _strip(re.sub(r"<br\s*/?>", ", ", pos)) or None}
    if not found or (partial and games == 0):
        return {"games": None, "goals": None, "partial": found, **extra}
    return {"games": games, "goals": goals, "partial": partial, **extra}


def _idol_articles() -> dict:
    p = WIKI_DIR / "idolos.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@lru_cache(maxsize=1)
def idols() -> list[Idol]:
    """Os 30 maiores ídolos (O Globo/Extra, 11/05/2020), como listados no artigo do clube.

    Números: 1º o ranking oficial do clube (artigo de recordes, só os 20 primeiros);
    se o jogador não estiver lá, a caixa de informações do próprio artigo (idolos.json).
    """
    raw = _read("clube")
    m = re.search(r"=== Maiores ídolos ===(.*?)\n==[^=]", raw, flags=re.S)
    text = m.group(1) if m else ""
    arts = _idol_articles()
    out: list[Idol] = []
    for link, disp, rank in re.findall(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\] \((\d+)º\)", text):
        disp = disp or link
        a = arts.get(link, {})
        games, goals = _lookup(appearances(), link, disp), _lookup(scorers(), link, disp)
        src_g = src_gl = "recordes" if games is not None else None
        src_gl = "recordes" if goals is not None else None
        if games is None and a.get("games") is not None:
            games, src_g = a["games"], "artigo"
        if goals is None and a.get("goals") is not None and (src_g == "artigo" or a.get("games") is not None):
            goals, src_gl = a["goals"], "artigo"
        out.append(Idol(int(rank), re.sub(r"\s*\(anos 1980\)", "", disp), link, games, goals,
                        a.get("photo"), a.get("position"), a.get("years"), src_g, src_gl,
                        bool(a.get("partial")), a.get("title"), a.get("revid")))
    return sorted(out, key=lambda i: i.rank)


