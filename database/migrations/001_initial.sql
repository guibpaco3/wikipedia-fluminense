-- Esquema inicial da Wikipédia do Fluminense.
-- SQL mantido o mais portável possível (SQLite -> PostgreSQL).
-- Convenções:
--   reliability : 'alta' | 'media' | 'baixa'
--   status      : 'verificado' | 'nao_verificado' | 'divergente' | 'rejeitado'

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- ---------------------------------------------------------------- Fontes
CREATE TABLE sources (
    id                  INTEGER PRIMARY KEY,
    code                TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    kind                TEXT NOT NULL,          -- dataset | api | site | livro | manual
    base_url            TEXT,
    license             TEXT,
    default_reliability TEXT NOT NULL DEFAULT 'media',
    automated           INTEGER NOT NULL DEFAULT 0,
    notes               TEXT
);

CREATE TABLE collection_runs (
    id          INTEGER PRIMARY KEY,
    source_id   INTEGER NOT NULL REFERENCES sources(id),
    collector   TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL DEFAULT 'executando',  -- executando | ok | erro | parcial
    inserted    INTEGER NOT NULL DEFAULT 0,
    updated     INTEGER NOT NULL DEFAULT 0,
    unchanged   INTEGER NOT NULL DEFAULT 0,
    rejected    INTEGER NOT NULL DEFAULT 0,
    message     TEXT
);

-- Proveniência por campo: "valor X do campo Y da entidade Z veio da fonte W".
CREATE TABLE field_sources (
    id           INTEGER PRIMARY KEY,
    entity_type  TEXT NOT NULL,
    entity_id    INTEGER NOT NULL,
    field        TEXT NOT NULL,
    value        TEXT,
    source_id    INTEGER NOT NULL REFERENCES sources(id),
    source_ref   TEXT,                    -- identificador do registro na fonte
    url          TEXT,
    collected_at TEXT NOT NULL,
    reliability  TEXT NOT NULL DEFAULT 'media',
    status       TEXT NOT NULL DEFAULT 'nao_verificado',
    UNIQUE (entity_type, entity_id, field, source_id)
);
CREATE INDEX ix_field_sources_entity ON field_sources(entity_type, entity_id);

CREATE TABLE discrepancies (
    id           INTEGER PRIMARY KEY,
    entity_type  TEXT NOT NULL,
    entity_id    INTEGER NOT NULL,
    field        TEXT NOT NULL,
    current_value TEXT,
    current_source_id INTEGER REFERENCES sources(id),
    new_value    TEXT,
    new_source_id INTEGER REFERENCES sources(id),
    new_url      TEXT,
    detected_at  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'aberta',     -- aberta | mantido_atual | aceito_novo | ignorada
    resolved_by  TEXT,
    resolved_at  TEXT,
    note         TEXT
);
CREATE INDEX ix_discrepancies_status ON discrepancies(status);

-- ---------------------------------------------------------------- Geografia
CREATE TABLE countries (
    iso2      TEXT PRIMARY KEY,
    iso3      TEXT,
    name_pt   TEXT NOT NULL,
    name_en   TEXT,
    continent TEXT,
    lat       REAL,
    lon       REAL
);

CREATE TABLE cities (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    state        TEXT,
    country_iso2 TEXT REFERENCES countries(iso2),
    lat          REAL,
    lon          REAL,
    wikidata_id  TEXT,
    UNIQUE (name, state, country_iso2)
);

CREATE TABLE stadiums (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    official_name TEXT,
    city_id      INTEGER REFERENCES cities(id),
    country_iso2 TEXT REFERENCES countries(iso2),
    capacity     INTEGER,
    lat          REAL,
    lon          REAL,
    wikidata_id  TEXT,
    geo_status   TEXT NOT NULL DEFAULT 'nao_verificado'
);

CREATE TABLE stadium_aliases (
    alias_norm TEXT PRIMARY KEY,
    stadium_id INTEGER NOT NULL REFERENCES stadiums(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------- Clubes
CREATE TABLE teams (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    full_name    TEXT,
    state        TEXT,
    country_iso2 TEXT REFERENCES countries(iso2),
    crest_url    TEXT,
    wikidata_id  TEXT,
    is_fluminense INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE team_aliases (
    alias_norm TEXT PRIMARY KEY,
    team_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------- Competições
CREATE TABLE competitions (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    category     TEXT NOT NULL DEFAULT 'outro',  -- nacional | estadual | continental | mundial | amistoso | outro
    scope        TEXT NOT NULL DEFAULT 'profissional', -- profissional | base | feminino | outro esporte
    country_iso2 TEXT REFERENCES countries(iso2),
    organizer    TEXT,
    wikidata_id  TEXT,
    notes        TEXT
);

CREATE TABLE competition_editions (
    id             INTEGER PRIMARY KEY,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    season         TEXT NOT NULL,
    name           TEXT,
    format         TEXT,
    fluminense_result TEXT,          -- campeão, vice, 5º lugar... (cadastro manual/fonte)
    wikidata_id    TEXT,
    UNIQUE (competition_id, season)
);

-- ---------------------------------------------------------------- Pessoas
CREATE TABLE people (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    full_name    TEXT,
    birth_date   TEXT,
    death_date   TEXT,
    nationality_iso2 TEXT REFERENCES countries(iso2),
    position     TEXT,
    photo_url    TEXT,
    wikidata_id  TEXT UNIQUE,
    bio          TEXT,
    name_norm    TEXT NOT NULL
);
CREATE INDEX ix_people_name_norm ON people(name_norm);

CREATE TABLE person_aliases (
    alias_norm TEXT NOT NULL,
    person_id  INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    context    TEXT NOT NULL DEFAULT 'geral',   -- jogador | tecnico | geral
    PRIMARY KEY (alias_norm, context)
);

CREATE TABLE player_spells (
    id         INTEGER PRIMARY KEY,
    person_id  INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    start_date TEXT,
    end_date   TEXT,
    notes      TEXT,
    UNIQUE (person_id, start_date)
);

CREATE TABLE coach_spells (
    id         INTEGER PRIMARY KEY,
    person_id  INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    start_date TEXT,
    end_date   TEXT,
    interim    INTEGER NOT NULL DEFAULT 0,
    notes      TEXT,
    UNIQUE (person_id, start_date)
);

CREATE TABLE presidencies (
    id         INTEGER PRIMARY KEY,
    person_id  INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    start_date TEXT,
    end_date   TEXT,
    highlights TEXT,
    UNIQUE (person_id, start_date)
);

CREATE TABLE referees (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    country_iso2 TEXT REFERENCES countries(iso2),
    federation   TEXT,
    notes        TEXT
);

-- ---------------------------------------------------------------- Uniformes
CREATE TABLE kits (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT NOT NULL,   -- titular | reserva | terceiro | especial | historico
    season      TEXT,
    description TEXT,
    image_url   TEXT
);

-- ---------------------------------------------------------------- Partidas
CREATE TABLE matches (
    id               INTEGER PRIMARY KEY,
    natural_key      TEXT NOT NULL UNIQUE,      -- AAAA-MM-DD|adversario_norm
    date             TEXT NOT NULL,             -- ISO AAAA-MM-DD
    kickoff          TEXT,                      -- HH:MM (horário local)
    competition_id   INTEGER REFERENCES competitions(id),
    edition_id       INTEGER REFERENCES competition_editions(id),
    stage            TEXT,
    round            TEXT,
    home_team_id     INTEGER NOT NULL REFERENCES teams(id),
    away_team_id     INTEGER NOT NULL REFERENCES teams(id),
    opponent_id      INTEGER NOT NULL REFERENCES teams(id),
    flu_side         TEXT NOT NULL,             -- mandante | visitante | neutro
    flu_goals        INTEGER,
    opp_goals        INTEGER,
    flu_goals_ht     INTEGER,
    opp_goals_ht     INTEGER,
    flu_penalties    INTEGER,
    opp_penalties    INTEGER,
    stadium_id       INTEGER REFERENCES stadiums(id),
    city_id          INTEGER REFERENCES cities(id),
    country_iso2     TEXT REFERENCES countries(iso2),
    country_status   TEXT NOT NULL DEFAULT 'nao_verificado',
    attendance       INTEGER,
    referee_id       INTEGER REFERENCES referees(id),
    referee_status   TEXT NOT NULL DEFAULT 'nao_identificado', -- confirmado | nao_confirmado | nao_identificado
    flu_kit_id       INTEGER REFERENCES kits(id),
    kit_status       TEXT NOT NULL DEFAULT 'nao_identificado', -- confirmado | nao_identificado
    kit_evidence     TEXT,
    opp_kit          TEXT,
    flu_coach_id     INTEGER REFERENCES people(id),
    opp_coach        TEXT,
    flu_formation    TEXT,
    notes            TEXT,
    reliability      TEXT NOT NULL DEFAULT 'media',
    verification_status TEXT NOT NULL DEFAULT 'nao_verificado',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    CHECK (flu_side IN ('mandante', 'visitante', 'neutro')),
    CHECK (flu_goals IS NULL OR flu_goals >= 0),
    CHECK (opp_goals IS NULL OR opp_goals >= 0)
);
CREATE INDEX ix_matches_date ON matches(date);
CREATE INDEX ix_matches_opponent ON matches(opponent_id);
CREATE INDEX ix_matches_competition ON matches(competition_id);
CREATE INDEX ix_matches_referee ON matches(referee_id);
CREATE INDEX ix_matches_kit ON matches(flu_kit_id);
CREATE INDEX ix_matches_country ON matches(country_iso2);
CREATE INDEX ix_matches_stadium ON matches(stadium_id);

-- Vínculo partida <-> registro em cada fonte (atualização incremental).
CREATE TABLE match_source_refs (
    match_id   INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    source_id  INTEGER NOT NULL REFERENCES sources(id),
    source_ref TEXT NOT NULL,
    url        TEXT,
    row_hash   TEXT,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (source_id, source_ref)
);
CREATE INDEX ix_msr_match ON match_source_refs(match_id);

CREATE TABLE match_officials (
    match_id   INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    referee_id INTEGER NOT NULL REFERENCES referees(id),
    role       TEXT NOT NULL,     -- assistente_1 | assistente_2 | quarto_arbitro | var
    PRIMARY KEY (match_id, role)
);

CREATE TABLE match_events (
    id          INTEGER PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,   -- gol | gol_penalti | gol_contra | amarelo | vermelho
    minute      INTEGER,
    for_fluminense INTEGER NOT NULL,   -- 1 = evento a favor/do Flu
    person_id   INTEGER REFERENCES people(id),
    player_name TEXT,                  -- nome como aparece na fonte
    source_id   INTEGER REFERENCES sources(id),
    UNIQUE (match_id, event_type, minute, player_name, for_fluminense)
);
CREATE INDEX ix_events_match ON match_events(match_id);
CREATE INDEX ix_events_person ON match_events(person_id);

CREATE TABLE match_lineups (
    match_id   INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    person_id  INTEGER NOT NULL REFERENCES people(id),
    starter    INTEGER NOT NULL DEFAULT 1,
    shirt_number INTEGER,
    source_id  INTEGER REFERENCES sources(id),
    PRIMARY KEY (match_id, person_id)
);

-- ---------------------------------------------------------------- Títulos e história
CREATE TABLE titles (
    id             INTEGER PRIMARY KEY,
    competition_id INTEGER REFERENCES competitions(id),
    edition_id     INTEGER REFERENCES competition_editions(id),
    season         TEXT,
    name           TEXT NOT NULL,
    final_match_id INTEGER REFERENCES matches(id),
    coach_id       INTEGER REFERENCES people(id),
    official       INTEGER,            -- NULL = não informado
    context        TEXT,
    wikidata_id    TEXT UNIQUE,
    reliability    TEXT NOT NULL DEFAULT 'media',
    verification_status TEXT NOT NULL DEFAULT 'nao_verificado'
);

CREATE TABLE articles (
    id         INTEGER PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    title      TEXT NOT NULL,
    category   TEXT NOT NULL DEFAULT 'historia',
    summary    TEXT,
    body_md    TEXT NOT NULL,
    references_md TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE timeline_events (
    id          INTEGER PRIMARY KEY,
    date        TEXT NOT NULL,          -- AAAA, AAAA-MM ou AAAA-MM-DD
    title       TEXT NOT NULL,
    description TEXT,
    article_id  INTEGER REFERENCES articles(id),
    match_id    INTEGER REFERENCES matches(id),
    source_text TEXT
);

-- ---------------------------------------------------------------- Administração
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY,
    at          TEXT NOT NULL,
    username    TEXT NOT NULL,
    action      TEXT NOT NULL,
    entity_type TEXT,
    entity_id   INTEGER,
    details     TEXT
);
