"""Painel administrativo (protegido por senha)."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from collectors import brasileirao_dataset, csv_import, wikidata
from components import data
from core import config
from core.auth import LoginGuard
from database.connection import connect, query_df, query_one
from database.models import COMPETITION_CATEGORIES, KIT_CATEGORIES, RELIABILITY, VERIFICATION
from database.repository import (TRACKED_FIELDS, audit, manual_source_id, merge_people, record_field, resolve_person,
                                 resolve_referee)
from modules.coaches import merge_suggestions
from modules.search import rebuild_index
from modules.statistics import score_text

st.title("🔒 Administração")

# ------------------------------------------------------------------ autenticação
if not st.session_state.get("admin_user"):
    if not config.ADMIN_PASSWORD_HASH:
        st.error("Painel desativado: nenhuma senha configurada. Rode `python scripts/set_admin_password.py` "
                 "e reinicie o aplicativo.")
        st.stop()
    guard = LoginGuard(st.session_state)
    if guard.locked_for():
        st.error(f"Muitas tentativas. Tente novamente em {guard.locked_for()} s.")
        st.stop()
    with st.form("login"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if guard.attempt(u, p, config.ADMIN_USER, config.ADMIN_PASSWORD_HASH):
                st.session_state["admin_user"] = u
                st.rerun()
            st.error("Credenciais inválidas.")
    st.stop()

USER = st.session_state["admin_user"]
c1, c2 = st.columns([5, 1])
c1.caption(f"Conectado como **{USER}**. Toda alteração é registrada na auditoria.")
if c2.button("Sair"):
    st.session_state.pop("admin_user")
    st.rerun()


def after_change(msg: str = "Salvo.") -> None:
    rebuild_index()
    data.clear()
    st.success(msg)


def show_result(r: dict) -> None:
    (st.success if r["status"] == "ok" else st.warning)(
        f"{r['collector']}: {r['status']} — " + ", ".join(f"{k}={v}" for k, v in r.items()
                                                          if k not in ("collector", "status", "messages")))
    if r["messages"]:
        with st.expander("Mensagens"):
            st.code("\n".join(r["messages"][:300]))


tabs = st.tabs(["🔄 Atualização", "⚽ Partidas", "🗃️ Cadastros", "👤 Pessoas", "✅ Revisão", "🧾 Auditoria"])

# ------------------------------------------------------------------ atualização
with tabs[0]:
    st.markdown("#### Coleta automática (incremental)")
    st.caption("Registros sem alteração desde a última coleta são ignorados.")
    a, b = st.columns(2)
    if a.button("Brasileirão Dataset (Série A 2003–)", width="stretch"):
        with st.spinner("Baixando e comparando…"):
            show_result(brasileirao_dataset.collect())
        after_change("Atualização concluída.")
    if b.button("Wikidata: títulos, jogadores e técnicos", width="stretch"):
        with st.spinner("Consultando o Wikidata…"):
            show_result(wikidata.collect(("titles", "players", "coaches")))
        after_change("Atualização concluída.")
    pending = query_one("SELECT COUNT(*) AS n FROM stadiums WHERE wikidata_id IS NULL")["n"]
    st.markdown(f"#### Geolocalização de estádios ({pending} pendentes)")
    st.caption("Feita em lotes (~3 requisições por estádio, com pausa entre elas). "
               "Resultados entram como 'não verificado'.")
    batch = st.number_input("Estádios por lote", 1, 50, 15)
    if st.button("Geolocalizar próximo lote", disabled=not pending):
        with st.spinner("Consultando…"):
            from collectors.base import run_collector
            show_result(run_collector("wikidata:stadiums", "wikidata",
                                      lambda c, n, m: wikidata.stadiums(c, n, m, limit=int(batch))))
        after_change()
    st.markdown("#### Importar CSV padronizado")
    st.download_button("Baixar modelo de CSV", csv_import.template(), "modelo_partidas.csv", "text/csv")
    with st.expander("Formato das colunas"):
        st.code(csv_import.__doc__)
    up = st.file_uploader("Arquivo CSV (UTF-8)", type="csv")
    if up and st.button("Importar"):
        show_result(csv_import.import_csv(up.getvalue().decode("utf-8-sig"), USER))
        after_change()
    if st.button("Reconstruir índice de busca"):
        st.success(f"{rebuild_index()} documentos indexados.")

# ------------------------------------------------------------------ partidas
with tabs[1]:
    st.markdown("#### Localizar partida")
    q1, q2 = st.columns(2)
    d = q1.date_input("Data", value=None, min_value=date(1902, 7, 21), format="DD/MM/YYYY", key="adm_date")
    opp = q2.text_input("Adversário contém", key="adm_opp")
    sql, params = "SELECT * FROM v_matches WHERE 1=1", []
    if d:
        sql += " AND date = ?"
        params.append(d.isoformat())
    if opp:
        sql += " AND opponent LIKE ?"
        params.append(f"%{opp}%")
    found = query_df(sql + " ORDER BY date DESC LIMIT 200", params)
    if found.empty:
        st.info("Nenhuma partida. Para cadastrar uma nova, use a importação CSV (fonte = manual).")
    else:
        labels = {int(r["id"]): f"{r['date']} · {score_text(r)} · {r['competition'] or ''}" for r in found.to_dict("records")}
        mid = st.selectbox("Partida", list(labels), format_func=labels.get)
        m = query_one("SELECT * FROM matches WHERE id = ?", (mid,))
        stad = data.options("SELECT id, name FROM stadiums ORDER BY name")
        refs = data.options("SELECT id, name FROM referees ORDER BY name")
        kits = data.options("SELECT id, name FROM kits ORDER BY name")
        comps = data.options("SELECT id, name FROM competitions ORDER BY name")
        ctry = data.options("SELECT iso2, name_pt FROM countries ORDER BY name_pt")
        none = [None]
        with st.form(f"match_{mid}"):
            st.caption("Toda alteração exige a referência que a sustenta (URL, livro, jornal, foto).")
            f1, f2, f3 = st.columns(3)
            kickoff = f1.text_input("Horário (HH:MM)", m["kickoff"] or "")
            stage = f2.text_input("Fase", m["stage"] or "")
            rnd = f3.text_input("Rodada", m["round"] or "")
            comp = f1.selectbox("Competição", none + list(comps), format_func=lambda x: comps.get(x, "—"),
                                index=(none + list(comps)).index(m["competition_id"]) if m["competition_id"] in comps else 0)
            fg = f2.number_input("Gols do Flu", 0, 40, m["flu_goals"] or 0)
            og = f3.number_input("Gols do adversário", 0, 40, m["opp_goals"] or 0)
            fht = f2.number_input("Gols do Flu no intervalo (-1 = não informado)", -1, 40,
                                  -1 if m["flu_goals_ht"] is None else m["flu_goals_ht"])
            oht = f3.number_input("Gols do adversário no intervalo (-1 = não informado)", -1, 40,
                                  -1 if m["opp_goals_ht"] is None else m["opp_goals_ht"])
            stadium = f1.selectbox("Estádio", none + list(stad), format_func=lambda x: stad.get(x, "—"),
                                   index=(none + list(stad)).index(m["stadium_id"]) if m["stadium_id"] in stad else 0)
            country = f2.selectbox("País", none + list(ctry), format_func=lambda x: ctry.get(x, "—"),
                                   index=(none + list(ctry)).index(m["country_iso2"]) if m["country_iso2"] in ctry else 0)
            country_status = f3.selectbox("Status do país", ["verificado", "inferido", "nao_verificado"],
                                          index=["verificado", "inferido", "nao_verificado"].index(m["country_status"])
                                          if m["country_status"] in ("verificado", "inferido", "nao_verificado") else 2)
            att = f1.number_input("Público (0 = não informado)", 0, 250000, m["attendance"] or 0)
            new_ref = f2.text_input("Árbitro (novo nome, se não estiver na lista)")
            ref = f2.selectbox("Árbitro", none + list(refs), format_func=lambda x: refs.get(x, "—"),
                               index=(none + list(refs)).index(m["referee_id"]) if m["referee_id"] in refs else 0)
            ref_status = f3.selectbox("Status do árbitro", ["nao_identificado", "nao_confirmado", "confirmado"],
                                      index=["nao_identificado", "nao_confirmado", "confirmado"].index(m["referee_status"]))
            kit = f1.selectbox("Uniforme do Flu", none + list(kits), format_func=lambda x: kits.get(x, "—"),
                               index=(none + list(kits)).index(m["flu_kit_id"]) if m["flu_kit_id"] in kits else 0)
            kit_status = f2.selectbox("Status do uniforme", ["nao_identificado", "confirmado"],
                                      index=["nao_identificado", "confirmado"].index(m["kit_status"]))
            kit_ev = f3.text_input("Evidência do uniforme (foto/registro)", m["kit_evidence"] or "")
            opp_kit = f1.text_input("Uniforme do adversário", m["opp_kit"] or "")
            rel = f2.selectbox("Confiabilidade", RELIABILITY, index=RELIABILITY.index(m["reliability"]))
            ver = f3.selectbox("Verificação", VERIFICATION, index=VERIFICATION.index(m["verification_status"]))
            notes = st.text_area("Observações", m["notes"] or "")
            ref_url = st.text_input("Referência que sustenta a alteração (obrigatória)")
            if st.form_submit_button("Salvar partida"):
                if not ref_url.strip():
                    st.error("Informe a referência.")
                elif kit_status == "confirmado" and (not kit or not kit_ev.strip()):
                    st.error("Uniforme confirmado exige o uniforme e a evidência.")
                else:
                    with connect() as c:
                        src = manual_source_id(c)
                        if new_ref.strip():
                            ref = resolve_referee(c, new_ref)
                        new = {"kickoff": kickoff or None, "stage": stage or None, "round": rnd or None,
                               "competition_id": comp, "flu_goals": int(fg), "opp_goals": int(og),
                               "flu_goals_ht": None if fht < 0 else int(fht), "opp_goals_ht": None if oht < 0 else int(oht),
                               "stadium_id": stadium, "country_iso2": country, "country_status": country_status,
                               "attendance": int(att) or None, "referee_id": ref,
                               "referee_status": ref_status if ref else "nao_identificado",
                               "flu_kit_id": kit, "kit_status": kit_status if kit else "nao_identificado",
                               "kit_evidence": kit_ev or None, "opp_kit": opp_kit or None, "reliability": rel,
                               "verification_status": ver, "notes": notes or None}
                        changed = {k: v for k, v in new.items() if m[k] != v}
                        if changed:
                            sets = ", ".join(f"{k} = ?" for k in changed)
                            c.execute(f"UPDATE matches SET {sets}, updated_at = datetime('now') WHERE id = ?",
                                      [*changed.values(), mid])
                            for k, v in changed.items():
                                record_field(c, "match", mid, k, v, src, f"admin:{USER}", ref_url, "alta",
                                             "verificado" if ver == "verificado" else "nao_verificado")
                            audit(c, USER, "editar_partida", "match", mid,
                                  {"antes": {k: m[k] for k in changed}, "depois": changed, "referencia": ref_url})
                    after_change(f"{len(changed)} campo(s) alterado(s)." if changed else "Nada mudou.")

        st.markdown("#### Escalação do Fluminense")
        people = data.options("SELECT id, name FROM people ORDER BY name")
        current = query_df("SELECT person_id FROM match_lineups WHERE match_id = ?", (mid,))["person_id"].tolist()
        with st.form(f"lineup_{mid}"):
            sel = st.multiselect("Jogadores que atuaram", list(people), default=[p for p in current if p in people],
                                 format_func=people.get)
            newp = st.text_input("Adicionar jogador não cadastrado (nomes separados por ;)")
            lref = st.text_input("Referência da escalação")
            if st.form_submit_button("Salvar escalação"):
                if not lref.strip():
                    st.error("Informe a referência.")
                else:
                    with connect() as c:
                        src = manual_source_id(c)
                        ids = list(sel) + [resolve_person(c, n, "jogador") for n in newp.split(";") if n.strip()]
                        c.execute("DELETE FROM match_lineups WHERE match_id = ?", (mid,))
                        for pid in ids:
                            c.execute("INSERT OR IGNORE INTO match_lineups (match_id, person_id, source_id) "
                                      "VALUES (?, ?, ?)", (mid, pid, src))
                        record_field(c, "match", mid, "lineup", len(ids), src, f"admin:{USER}", lref, "alta")
                        audit(c, USER, "escalacao", "match", mid, {"jogadores": ids, "referencia": lref})
                    after_change()

# ------------------------------------------------------------------ cadastros genéricos
TABLES = {
    "Árbitros": ("referees", ["id", "name", "country_iso2", "federation", "notes"], {}),
    "Uniformes": ("kits", ["id", "name", "category", "season", "description", "image_url"],
                  {"category": st.column_config.SelectboxColumn(options=list(KIT_CATEGORIES), required=True)}),
    "Competições": ("competitions", ["id", "name", "category", "scope", "country_iso2", "organizer", "notes"],
                    {"category": st.column_config.SelectboxColumn(options=list(COMPETITION_CATEGORIES)),
                     "scope": st.column_config.SelectboxColumn(options=["profissional", "base", "feminino", "outro esporte"])}),
    "Edições (resultado final)": ("competition_editions", ["id", "competition_id", "season", "name", "format",
                                                           "fluminense_result"], {}),
    "Títulos": ("titles", ["id", "name", "season", "competition_id", "edition_id", "official", "coach_id",
                           "final_match_id", "context", "reliability", "verification_status"],
                {"verification_status": st.column_config.SelectboxColumn(options=list(VERIFICATION)),
                 "reliability": st.column_config.SelectboxColumn(options=list(RELIABILITY))}),
    "Estádios": ("stadiums", ["id", "name", "official_name", "city_id", "country_iso2", "capacity", "lat", "lon",
                              "geo_status"], {}),
    "Cidades": ("cities", ["id", "name", "state", "country_iso2", "lat", "lon"], {}),
    "Clubes": ("teams", ["id", "name", "full_name", "state", "country_iso2", "crest_url"], {}),
    "Artigos históricos": ("articles", ["id", "slug", "title", "category", "summary", "body_md", "references_md",
                                        "created_at", "updated_at"], {}),
    "Linha do tempo": ("timeline_events", ["id", "date", "title", "description", "article_id", "match_id",
                                           "source_text"], {}),
}

with tabs[2]:
    choice = st.selectbox("Tabela", list(TABLES))
    table, cols, cfg = TABLES[choice]
    st.caption("Edite células, adicione linhas no final ou selecione linhas e apague. Depois clique em Salvar.")
    if table == "articles":
        st.caption("Para artigos, `created_at`/`updated_at` são preenchidos automaticamente se vazios.")
    orig = query_df(f"SELECT {', '.join(cols)} FROM {table} ORDER BY id")
    edited = st.data_editor(orig, num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_{table}",
                            column_config={"id": st.column_config.NumberColumn(disabled=True), **cfg}, height=480)
    if st.button("Salvar alterações", key=f"save_{table}"):
        try:
            with connect() as c:
                orig_ids = set(orig["id"].dropna().astype(int))
                kept_ids = set(edited["id"].dropna().astype(int))
                for rid in orig_ids - kept_ids:
                    c.execute(f"DELETE FROM {table} WHERE id = ?", (rid,))
                    audit(c, USER, "apagar", table, rid)
                fields = [x for x in cols if x != "id"]
                o = orig.set_index("id")
                for row in edited.to_dict("records"):
                    vals = {k: (None if pd.isna(row[k]) or row[k] == "" else row[k]) for k in fields}
                    if table == "articles":
                        vals["updated_at"] = date.today().isoformat()
                        vals["created_at"] = vals["created_at"] or date.today().isoformat()
                    if pd.isna(row["id"]):
                        rid = c.insert(f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                                       list(vals.values()))
                        audit(c, USER, "criar", table, rid, vals)
                    else:
                        rid = int(row["id"])
                        before = {k: (None if pd.isna(o.loc[rid, k]) else o.loc[rid, k]) for k in fields}
                        diff = {k: v for k, v in vals.items() if str(before[k]) != str(v) and k != "updated_at"}
                        if diff:
                            c.execute(f"UPDATE {table} SET {', '.join(f'{k} = ?' for k in vals)} WHERE id = ?",
                                      [*vals.values(), rid])
                            audit(c, USER, "editar", table, rid, {"antes": {k: before[k] for k in diff}, "depois": diff})
            after_change()
        except Exception as exc:
            st.error(f"Não foi possível salvar: {exc}")

    st.markdown("#### Presidentes")
    with st.form("president"):
        p1, p2, p3 = st.columns(3)
        pname = p1.text_input("Nome")
        pstart = p2.text_input("Início do mandato (AAAA ou AAAA-MM-DD)")
        pend = p3.text_input("Fim do mandato")
        phigh = st.text_area("Principais acontecimentos (com fontes)")
        if st.form_submit_button("Cadastrar presidente") and pname.strip():
            with connect() as c:
                pid = resolve_person(c, pname, "geral")
                c.execute("INSERT OR REPLACE INTO presidencies (person_id, start_date, end_date, highlights) "
                          "VALUES (?, ?, ?, ?)", (pid, pstart or None, pend or None, phigh or None))
                audit(c, USER, "presidente", "person", pid, {"inicio": pstart, "fim": pend})
            after_change()

# ------------------------------------------------------------------ pessoas
with tabs[3]:
    st.markdown("#### Sugestões de unificação de técnicos")
    st.caption("Nome abreviado do dataset × cadastro completo do Wikidata, quando sobrenome e período coincidem.")
    sug = merge_suggestions()
    if sug.empty:
        st.caption("Nenhuma sugestão.")
    for r in sug.to_dict("records"):
        a, b = st.columns([5, 1])
        a.write(f"**{r['Unir (como no dataset)']}** ({r['Jogos']} jogos, {r['Período dos jogos']}) → "
                f"**{r['Manter (completo)']}**")
        if b.button("Unir", key=f"merge_{r['keep_id']}_{r['drop_id']}"):
            with connect() as c:
                merge_people(c, r["keep_id"], r["drop_id"], USER)
            after_change("Cadastros unidos.")
            st.rerun()
    st.markdown("#### Unir duas pessoas manualmente")
    people = data.options("SELECT id, name || ' (#' || id || ')' FROM people ORDER BY name")
    m1, m2 = st.columns(2)
    keep = m1.selectbox("Manter", list(people), format_func=people.get, index=None, key="keep_p")
    drop = m2.selectbox("Unir e remover", list(people), format_func=people.get, index=None, key="drop_p")
    if st.button("Unir cadastros", disabled=not (keep and drop and keep != drop)):
        with connect() as c:
            merge_people(c, keep, drop, USER)
        after_change("Cadastros unidos.")
    st.markdown("#### Editar pessoa")
    who = st.selectbox("Pessoa", list(people), format_func=people.get, index=None, key="edit_p")
    if who:
        p = query_one("SELECT * FROM people WHERE id = ?", (who,))
        with st.form("person_form"):
            name = st.text_input("Nome de exibição", p["name"])
            full = st.text_input("Nome completo", p["full_name"] or "")
            birth = st.text_input("Nascimento (AAAA-MM-DD)", p["birth_date"] or "")
            nat = st.text_input("Nacionalidade (ISO alfa-2)", p["nationality_iso2"] or "")
            pos = st.text_input("Posição", p["position"] or "")
            bio = st.text_area("Biografia (com fontes)", p["bio"] or "")
            if st.form_submit_button("Salvar"):
                with connect() as c:
                    c.execute("UPDATE people SET name=?, full_name=?, birth_date=?, nationality_iso2=?, position=?, bio=? "
                              "WHERE id=?", (name, full or None, birth or None, nat.upper() or None, pos or None,
                                             bio or None, who))
                    audit(c, USER, "editar_pessoa", "person", who, {"nome": name})
                after_change()

# ------------------------------------------------------------------ revisão
with tabs[4]:
    st.markdown("#### Divergências abertas")
    disc = query_df("SELECT d.*, s.name AS fonte FROM discrepancies d LEFT JOIN sources s ON s.id = d.new_source_id "
                    "WHERE d.status = 'aberta' ORDER BY d.id LIMIT 100")
    if disc.empty:
        st.caption("Nenhuma divergência aberta.")
    for r in disc.to_dict("records"):
        a, b, c_ = st.columns([4, 1, 1])
        a.write(f"{r['entity_type']} #{r['entity_id']} · **{r['field']}**: atual `{r['current_value']}` × "
                f"`{r['new_value']}` ({r['fonte']})")
        if b.button("Manter atual", key=f"keep_{r['id']}"):
            with connect() as c:
                c.execute("UPDATE discrepancies SET status='mantido_atual', resolved_by=?, resolved_at=datetime('now') "
                          "WHERE id=?", (USER, r["id"]))
                audit(c, USER, "divergencia_mantida", r["entity_type"], r["entity_id"], {"campo": r["field"]})
            after_change()
            st.rerun()
        if c_.button("Aceitar nova", key=f"acc_{r['id']}") and r["entity_type"] == "match"                 and r["field"] in TRACKED_FIELDS:
            with connect() as c:
                c.execute(f"UPDATE matches SET {r['field']} = ? WHERE id = ?", (r["new_value"], r["entity_id"]))
                c.execute("UPDATE discrepancies SET status='aceito_novo', resolved_by=?, resolved_at=datetime('now') "
                          "WHERE id=?", (USER, r["id"]))
                audit(c, USER, "divergencia_aceita", "match", r["entity_id"], {"campo": r["field"], "valor": r["new_value"]})
            after_change()
            st.rerun()
    st.markdown("#### Títulos aguardando verificação")
    st.dataframe(query_df("SELECT id, season, name, reliability, verification_status FROM titles "
                          "WHERE verification_status = 'nao_verificado' ORDER BY season"), hide_index=True, width="stretch")
    st.caption("Para verificar, edite a tabela **Títulos** em Cadastros (status e contexto).")
    st.markdown("#### Partidas com baixa confiabilidade ou divergentes")
    st.dataframe(query_df("SELECT id, date, opponent, competition, reliability, verification_status FROM v_matches "
                          "WHERE reliability = 'baixa' OR verification_status = 'divergente' ORDER BY date"),
                 hide_index=True, width="stretch")

# ------------------------------------------------------------------ auditoria
with tabs[5]:
    st.dataframe(query_df("SELECT at AS Quando, username AS Usuário, action AS Ação, entity_type AS Entidade, "
                          "entity_id AS ID, details AS Detalhes FROM audit_log ORDER BY id DESC LIMIT 500"),
                 hide_index=True, width="stretch")
