# Wikipédia do Fluminense FC

*Uma enciclopédia digital da história, das conquistas e da trajetória do Fluminense Football Club.*

Aplicação Streamlit + SQLite em que **toda estatística é calculada do banco** e cada informação guarda
fonte, URL, data de coleta, confiabilidade e status de verificação. Nada é inventado: o que não tem fonte
aparece como "não informado", "não identificado" ou "não verificado".

## Como executar

```bash
pip install -r requirements.txt
python scripts/update_data.py          # cria o banco e coleta as fontes automáticas (~1 min)
python scripts/set_admin_password.py   # define usuário/senha do painel (grava hash em .env)
streamlit run app.py
```

Testes: `python -m pytest -q` (43 testes: banco, coletores, filtros, estatísticas, busca, autenticação e
renderização de todas as páginas).

> No Windows deste computador, o executável é `python3.13` (o alias `python` aponta para a Microsoft Store).

## Publicação (Streamlit Community Cloud)

O site publicado lê o banco versionado `data/wikipedia.db`. Fluxo de atualização:

1. Edite/colete **localmente** (painel admin local, `scripts/update_data.py`, código).
2. `git add -A && git commit -m "..." && git push` — o Streamlit Cloud reimplanta sozinho em ~1 min.

> O disco do Streamlit Cloud é temporário: alterações feitas no painel **do site publicado** se perdem na
> próxima reinicialização. Por isso o painel fica desativado lá (sem `ADMIN_PASSWORD_HASH` nos *Secrets*)
> e as edições são feitas na cópia local.

## Estrutura

```
app.py                 navegação, tema, busca global na barra lateral
core/                  configuração/logs, autenticação (PBKDF2), normalização de texto
database/              conexão (SQLite; preparada p/ PostgreSQL), migrações .sql versionadas,
                       modelos, repositório (upsert com proveniência, divergências, auditoria)
collectors/            cliente HTTP respeitoso, catálogo de fontes, validação,
                       brasileirao_dataset.py, wikidata.py, csv_import.py
modules/               filtros combináveis, estatísticas, cobertura, globo, busca,
                       partidas, jogadores, técnicos, competições, estádios, história
components/            tema, cards, tabelas clicáveis, calendário, globo 3D (Globe.gl), gráficos
views/                 páginas (nome "views/" evita o multipage automático do Streamlit)
scripts/               atualização incremental (CLI), senha do admin, base de países
tests/                 pytest (banco temporário com dados fictícios só de teste)
docs/                  ETAPA1_PLANEJAMENTO.md — viabilidade, fontes, modelo de dados
```

**Adicionar um módulo:** consultas em `modules/`, página em `views/`, uma linha em `PAGES` no `app.py`.
**Evoluir o banco:** novo arquivo `database/migrations/NNN_*.sql` (aplicado automaticamente).

## Dados atuais (26/11/2026)

| Conteúdo | Quantidade | Fonte | Situação |
|---|---|---|---|
| Partidas — total | 4.219 | ver linhas abaixo | confiabilidade média |
| Campeonato Carioca | 2.307 (1906–2024) | RSSSF Brasil | sem 2025/2026 (a fonte não tem) |
| Brasileirão (A, B, C, Taça Brasil, Robertão) | 1.587 (1960–2026) | RSSSF, Brasileirão Dataset, openfootball | 1996–1998 quase vazios (rodadas com duas datas); 2026 parcial |
| Copa do Brasil | 155 (1992–2025) | RSSSF, openfootball | anos 1989–1998 sem data por jogo na fonte |
| Libertadores / Sul-Americana / Recopa | 97 / 63 / 2 | RSSSF, openfootball | Sul-Americana 2025 parcial |
| Mundial de Clubes FIFA | 8 (2023, 2025) | openfootball | — |
| Gols/cartões detalhados | 3.162 eventos | idem | — |
| Jogadores com passagem | 803 | Wikidata | não verificado |
| Títulos | 46 | Wikidata | **incompleto**, não verificado |
| Técnicos | 9 passagens (Wikidata) + nomes do dataset | ambos | unificação no painel |
| Estádios | 100 nomes | dataset | geolocalização pendente |
| Árbitros, uniformes, presidentes, artigos | 0 | — | cadastro manual |

## Próximos passos (o que ainda falta)

1. **Geolocalizar estádios** (Painel → Atualização, em lotes) — habilita cidades e o mapa de estádios.
2. **Unificar técnicos** (Painel → Pessoas → sugestões automáticas).
3. **Lacunas de partidas** — importar via CSV padronizado (modelo no painel), com fonte: Carioca 2025–2026,
   Brasileirão 1996–1998, Copa do Brasil 1989–1998, Sul-Americana 2025 completa, Copa do Brasil 2026,
   jogos decididos no tribunal ("awd"), amistosos. Atualizar 2026 rodando
   `python scripts/update_data.py --skip-auto --rsssf` e o coletor openfootball (Painel → Atualização).
4. Revisar títulos (marcar verificado/oficial, completar Cariocas que faltam no Wikidata).
5. Cadastros manuais com fonte: árbitros, uniformes (com evidência), presidentes, artigos e linha do tempo.
6. Publicação: definir `ADMIN_PASSWORD_HASH` como segredo do servidor; para vários editores simultâneos,
   migrar para PostgreSQL (`DATABASE_URL`).
