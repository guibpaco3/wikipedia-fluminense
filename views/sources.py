"""Transparência: fontes, cobertura, completude e histórico de coletas."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import coverage_note
from modules import coverage

st.title("📚 Fontes e cobertura")
coverage_note(data.coverage_text())
s = data.coverage_summary()
st.write(f"**Última atualização da base:** {s.get('last_update') or 'nunca'}")

st.markdown("### Cobertura por competição")
st.dataframe(coverage.by_competition(), hide_index=True, width="stretch")
st.markdown("### Completude das informações")
st.caption("Percentual das partidas da base em que cada informação está preenchida.")
st.dataframe(coverage.field_completeness(), hide_index=True, width="stretch",
             column_config={"Cobertura %": st.column_config.ProgressColumn("Cobertura %", min_value=0, max_value=100,
                                                                          format="%.1f%%")})
st.markdown("### Partidas por fonte")
st.dataframe(coverage.by_source(), hide_index=True, width="stretch")
st.markdown("### Fontes investigadas")
st.dataframe(data.df("SELECT name AS Fonte, kind AS Tipo, CASE automated WHEN 1 THEN 'Automática' ELSE 'Manual' END "
                     "AS Coleta, license AS Licença, default_reliability AS Confiabilidade, notes AS Observações, "
                     "base_url AS URL FROM sources ORDER BY automated DESC, name"),
             hide_index=True, width="stretch", column_config={"URL": st.column_config.LinkColumn("URL")})
st.markdown("### Histórico de coletas")
st.dataframe(data.df("SELECT r.started_at AS Início, r.collector AS Coletor, r.status AS Situação, r.inserted AS Novos, "
                     "r.updated AS Atualizados, r.unchanged AS 'Sem alteração', r.rejected AS Rejeitados "
                     "FROM collection_runs r ORDER BY r.id DESC LIMIT 50"), hide_index=True, width="stretch")
st.markdown("### Divergências entre fontes")
st.dataframe(data.df("SELECT entity_type AS Entidade, entity_id AS ID, field AS Campo, current_value AS Atual, "
                     "new_value AS Divergente, status AS Situação FROM discrepancies ORDER BY id DESC LIMIT 200"),
             hide_index=True, width="stretch")
