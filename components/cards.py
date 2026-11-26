"""Cards de indicadores, bloco de retrospecto, tabelas de partidas e aviso de cobertura."""
from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from components.theme import RESULT_COLORS
from modules.statistics import Record, score_text

MATCH_PAGE = "views/match.py"


def fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return date.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)


def stat_cards(items: list[tuple]) -> None:
    """items: (rótulo, valor, nota opcional, cor 'g'|'r'|'n0')."""
    parts = []
    for it in items:
        label, value = it[0], it[1]
        note = it[2] if len(it) > 2 and it[2] else ""
        kind = it[3] if len(it) > 3 else "g"
        parts.append(f'<div class="wf-card {kind}"><div class="l">{html.escape(str(label))}</div>'
                     f'<div class="v">{html.escape(str(value))}</div>'
                     + (f'<div class="n">{html.escape(note)}</div>' if note else "") + "</div>")
    st.markdown(f'<div class="wf-cards">{"".join(parts)}</div>', unsafe_allow_html=True)


def coverage_note(text: str) -> None:
    st.markdown(f'<div class="wf-cov">ℹ️ {html.escape(text)}</div>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="wf-note">{text}</div>', unsafe_allow_html=True)


def record_block(r: Record, title: str | None = None) -> None:
    if title:
        st.markdown(f"#### {title}")
    if not r.matches:
        st.info("Nenhuma partida encontrada na base para estes critérios.")
        return
    pct = f"{r.points_pct:.1f}%" if r.points_pct is not None else "—"
    stat_cards([
        ("Partidas", fmt_int(r.matches), "" if r.with_score == r.matches else f"{r.with_score} com placar", "g"),
        ("Vitórias", fmt_int(r.wins), "", "g"), ("Empates", fmt_int(r.draws), "", "n0"),
        ("Derrotas", fmt_int(r.losses), "", "r"), ("Aproveitamento", pct, "pontos ganhos / disputados", "g"),
        ("Gols marcados", fmt_int(r.goals_for), "", "g"), ("Gols sofridos", fmt_int(r.goals_against), "", "r"),
        ("Saldo", f"{r.goal_diff:+d}", "", "g" if r.goal_diff >= 0 else "r"),
    ])
    cols = st.columns(3)
    for col, (label, m) in zip(cols, (("Maior vitória", r.biggest_win), ("Maior derrota", r.biggest_loss),
                                      ("Último confronto", r.last))):
        with col:
            st.caption(label)
            if m:
                st.page_link(MATCH_PAGE, label=f"{score_text(m)} · {fmt_date(m['date'])}",
                             query_params={"id": int(m["id"])}, icon="⚽")
            else:
                st.write("—")


def result_badge(res: str | None) -> str:
    if not res:
        return '<span class="wf-res" style="background:#B8BEBB">?</span>'
    return f'<span class="wf-res" style="background:{RESULT_COLORS[res]}">{res}</span>'


def matches_table(df: pd.DataFrame, key: str, height: int | None = None, extra_cols: list[str] | None = None) -> None:
    """Tabela pesquisável; clicar numa linha abre a página da partida."""
    if df.empty:
        st.info("Nenhuma partida encontrada.")
        return
    view = pd.DataFrame({
        "Data": pd.to_datetime(df["date"]).dt.strftime("%d/%m/%Y"),
        "Res.": df["result"].map({"V": "🟢 V", "E": "⚪ E", "D": "🔴 D"}).fillna("—"),
        "Partida": [score_text(m) for m in df.to_dict("records")],
        "Competição": df["competition"].fillna("—") + df["season"].map(lambda s: f" {s}" if s else ""),
        "Rodada/Fase": df["stage"].fillna(df["round"].map(lambda r: f"Rodada {r}" if r else None)).fillna(""),
        "Estádio": df["stadium"].fillna("Não informado"),
    })
    for c in extra_cols or []:
        view[c] = df[c].values
    st.caption(f"{len(df)} partida(s) · clique numa linha para abrir a página da partida")
    ev = st.dataframe(view, hide_index=True, key=key, on_select="rerun", selection_mode="single-row",
                      height=height or min(38 + 35 * len(view), 520), width="stretch")
    rows = ev.selection.rows if ev and hasattr(ev, "selection") else []
    if rows:
        st.switch_page(MATCH_PAGE, query_params={"id": int(df.iloc[rows[0]]["id"])})


def entity_table(df: pd.DataFrame, key: str, page: str, id_col: str = "id", hide: list[str] | None = None,
                 height: int | None = None, param: str = "id") -> None:
    """Tabela genérica de entidades: clicar abre a página da entidade."""
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return
    show = df.drop(columns=[c for c in [id_col, *(hide or [])] if c in df.columns])
    ev = st.dataframe(show, hide_index=True, key=key, on_select="rerun", selection_mode="single-row",
                      height=height or min(38 + 35 * len(show), 560), width="stretch")
    rows = ev.selection.rows if ev and hasattr(ev, "selection") else []
    if rows:
        st.switch_page(page, query_params={param: int(df.iloc[rows[0]][id_col])})
