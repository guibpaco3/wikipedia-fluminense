# Etapa 1 — Planejamento e viabilidade

Data da análise: 24/11/2026.

## 1. Viabilidade

O projeto é viável, mas **a completude histórica não pode ser obtida automaticamente**.
Os dados de 1902 até os anos 2000 existem principalmente em livros, jornais
(Hemeroteca Digital da Biblioteca Nacional), almanaques e no RSSSF. Não há fonte aberta,
estruturada e licenciada para reuso com todos os jogos do clube.

Por isso a arquitetura parte de três princípios:

1. **Cobertura explícita**: toda estatística vem acompanhada do período e das
   competições efetivamente cobertas pela base. Nunca "total histórico" sem ressalva.
2. **Proveniência por campo**: cada valor importante (placar, data, estádio, árbitro,
   uniforme, técnico) guarda fonte, URL, data de coleta, confiabilidade e status.
3. **Crescimento incremental**: coletores automáticos para o que é aberto; importação
   CSV padronizada e painel administrativo para todo o resto.

## 2. Fontes investigadas (teste real de acesso feito em 24/11/2026)

| Fonte | Resultado do teste | Decisão |
|---|---|---|
| SofaScore (API) | HTTP 403 para cliente identificado | **Não coletar.** Não contornar bloqueio. |
| WorldFootball.net | HTTP 403 | **Não coletar.** |
| Transfermarkt | HTTP 200, mas os termos proíbem extração automatizada | Somente transcrição manual com citação (CSV/painel). |
| oGol | HTTP 200, termos restringem reuso | Somente transcrição manual com citação. |
| RSSSF / RSSSF Brasil | Acessível; páginas em texto livre, formatos heterogêneos | Transcrição manual / parsers específicos futuros, com crédito. |
| **Brasileirão Dataset** (github.com/adaoduque/Brasileirao_Dataset) | HTTP 200, CSV aberto | **Coletor automático.** 856 jogos do Flu na Série A 2003–2024, técnicos, estádio, autores dos gols, cartões. Licença não declarada no repositório → uso com crédito, confiabilidade "média". |
| **Wikidata** (SPARQL, CC0) | HTTP 200 | **Coletor automático.** Títulos (P1346: 61 registros), 803 jogadores com vínculo (P54), técnicos recentes (P286), coordenadas de estádios (P625). Confiabilidade "média", status "não verificado". |
| Natural Earth | Domínio público | Base de países, continentes e coordenadas do globo. |
| Site oficial do Fluminense | Conteúdo editorial | Fonte de referência para cadastro manual (história, presidentes). |

## 3. O que é automático × manual

**Automático (nesta versão)**
- Partidas do Brasileirão Série A 2003–2024 (data, hora, mandante, placar, estádio, rodada,
  técnicos, gols com autor e minuto, cartões).
- Títulos registrados no Wikidata (para revisão).
- Jogadores com passagem pelo clube segundo o Wikidata (nome, nascimento, nacionalidade,
  posição, período).
- Técnicos com período no Wikidata.
- Geocodificação de estádios via Wikidata (cidade, coordenadas) — "não verificado".

**Manual (painel administrativo ou CSV padronizado)**
- Todas as partidas fora do Brasileirão 2003–2024 (Carioca, Libertadores, Copa do Brasil,
  Mundiais, amistosos, todo o período 1902–2002).
- **Árbitros** (nenhuma fonte aberta encontrada com licença de reuso).
- **Uniformes** (exigem fotografia/registro; nunca inferidos por mando de campo).
- Placar de intervalo, público, escalações completas.
- Presidentes, artigos históricos, linha do tempo.

## 4. Modelo de dados (resumo)

```
sources ──< collection_runs
   │
   └──< field_sources (entidade, campo, valor, fonte, url, coletado_em, confiabilidade, status)
   └──< discrepancies (valor A × valor B, fontes, status da revisão)

countries ──< cities ──< stadiums
teams (+ team_aliases)          competitions ──< competition_editions
referees    kits    people (jogadores, técnicos, presidentes, árbitros podem virar pessoas)

matches ── home_team, away_team, opponent, competition, edition, stadium, city, country,
   │       referee (+ status), kit do Flu (+ status), técnico do Flu, placar, intervalo,
   │       pênaltis, público, verification_status, reliability, natural_key UNIQUE
   ├──< match_officials (auxiliares)
   ├──< match_events (gols, gols contra, cartões)
   └──< match_lineups (jogadores do Flu na partida)

player_spells, coach_spells, presidencies, titles, articles, timeline_events
admin_users, audit_log, schema_migrations, meta, search_index (FTS5)
```

Controle de duplicidade: `natural_key = data + adversário` (um mesmo jogo vindo de duas fontes
é fundido; divergências de valor viram registros em `discrepancies`).

## 5. Arquitetura

```
wikipedia-fluminense/
  app.py                    navegação (st.navigation), tema, busca global na barra lateral
  core/                     configuração, logs, autenticação, utilidades de texto
  database/                 conexão (SQLite; adaptador preparado p/ PostgreSQL),
                            migrações versionadas (.sql), repositório (upsert, proveniência, auditoria)
  collectors/               cliente HTTP educado, coletores, normalização, validação
  modules/                  regras de negócio: filtros, estatísticas, calendário, globo,
                            busca, jogadores, técnicos, competições, estádios, história...
  components/               tema, cards, card de partida, calendário visual, globo 3D, gráficos
  views/                    páginas Streamlit (usado "views/" em vez de "pages/" para não
                            conflitar com o multipage automático do Streamlit)
  scripts/                  CLI de atualização incremental, senha do admin
  tests/                    pytest
  data/                     wikipedia.db, referências, importações CSV
```

Novos módulos = nova função em `modules/` + nova página em `views/` + registro em `app.py`.
Nenhuma página contém dados fixos: tudo vem do banco.

## 6. Limitações técnicas conhecidas

- A base inicial cobre principalmente **Brasileirão Série A 2003–2024**. O globo terá
  inicialmente apenas o Brasil até que jogos internacionais sejam cadastrados.
- Nomes de técnicos no dataset vêm abreviados ("L. Venker de Menezes"); a unificação com
  o nome completo é feita no painel (mesclagem de pessoas).
- Filtro por árbitro e por uniforme funcionam, mas mostram "sem dados confirmados" até haver
  cadastro manual.
- Globo 3D carrega Globe.gl e texturas via CDN (exige internet no navegador do usuário).
- Streamlit não tem rotas dinâmicas reais; páginas individuais usam `?id=` na URL.
- Migração para PostgreSQL: SQL escrito de forma portável e camada de conexão com
  adaptação de placeholders; FTS5 (busca) teria de virar `tsvector`.
