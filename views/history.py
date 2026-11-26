"""História do clube: artigos, linha do tempo e presidentes."""
from __future__ import annotations

import html

import streamlit as st

from components.cards import fmt_date, note
from modules import history

aid = st.query_params.get("id")
if aid:
    a = history.article(int(aid))
    if not a:
        st.error("Artigo não encontrado.")
        st.stop()
    st.page_link("views/history.py", label="← História")
    st.title(a["title"])
    st.caption(f"{a['category']} · atualizado em {fmt_date(a['updated_at'])}")
    st.markdown(a["body_md"])
    if a["references_md"]:
        st.markdown("#### Referências")
        st.markdown(a["references_md"])
    st.stop()

st.title("📜 História do Fluminense")
tab_a, tab_t, tab_p = st.tabs(["Artigos", "Linha do tempo", "Presidentes"])
with tab_a:
    arts = history.articles()
    if arts.empty:
        note("Nenhum artigo publicado ainda. Os artigos históricos (fundação, origem, evolução institucional, "
             "grandes campanhas, crises) são redigidos no painel administrativo, sempre com referências. "
             "Seções previstas: Fundação · Origem do clube · Futebol no Fluminense · Evolução institucional · "
             "Momentos históricos · Grandes campanhas · Conquistas · Crises e transformações.")
    for cat, grp in arts.groupby("category") if not arts.empty else []:
        st.markdown(f"#### {cat.capitalize()}")
        for r in grp.itertuples():
            st.page_link("views/history.py", label=f"{r.title}" + (f" — {r.summary}" if r.summary else ""),
                         query_params={"id": r.id}, icon="📄")
with tab_t:
    tl = history.timeline()
    if tl.empty:
        note("Linha do tempo ainda vazia — cadastre os marcos no painel (cada um com sua fonte).")
    else:
        items = "".join(
            f'<div class="i"><div class="dt">{html.escape(r.date)}</div><b>{html.escape(r.title)}</b>'
            f'<div>{html.escape(r.description or "")}</div>'
            f'<div style="font-size:.75rem;color:#7a847f">{html.escape(r.source_text or "")}</div></div>'
            for r in tl.itertuples())
        st.markdown(f'<div class="wf-tl">{items}</div>', unsafe_allow_html=True)
with tab_p:
    pr = history.presidents()
    if pr.empty:
        note("Nenhum presidente cadastrado ainda. O cadastro é manual (painel), com período de mandato e fonte. "
             "O Wikidata não registra a presidência do clube (propriedade P488 vazia em 24/11/2026).")
    else:
        for r in pr.itertuples():
            with st.expander(f"{r.Presidente} — {r.Início or '?'} a {r.Fim or '?'}"):
                st.write(r._6 or "_Sem resumo cadastrado._")
                t = history.titles_in_period(r.Início, r.Fim)
                st.caption("Títulos registrados no período do mandato:")
                if t.empty:
                    st.caption("Nenhum.")
                else:
                    st.dataframe(t, hide_index=True, width="stretch")
