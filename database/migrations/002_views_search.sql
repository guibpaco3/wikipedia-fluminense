-- Visão "achatada" das partidas, base de todas as consultas e estatísticas.
CREATE VIEW v_matches AS
SELECT
    m.id, m.date, m.kickoff,
    CAST(substr(m.date, 1, 4) AS INTEGER) AS year,
    CAST(substr(m.date, 6, 2) AS INTEGER) AS month,
    CAST(substr(m.date, 9, 2) AS INTEGER) AS day,
    m.flu_side, m.flu_goals, m.opp_goals, m.flu_goals_ht, m.opp_goals_ht,
    m.flu_penalties, m.opp_penalties,
    CASE WHEN m.flu_goals IS NULL OR m.opp_goals IS NULL THEN NULL
         WHEN m.flu_goals > m.opp_goals THEN 'V'
         WHEN m.flu_goals < m.opp_goals THEN 'D'
         ELSE 'E' END AS result,
    m.opponent_id, o.name AS opponent, o.country_iso2 AS opponent_country, o.crest_url AS opponent_crest,
    h.name AS home_team, a.name AS away_team,
    m.competition_id, c.name AS competition, c.category AS competition_category, c.scope AS competition_scope,
    m.edition_id, e.season AS season,
    m.stage, m.round,
    m.stadium_id, s.name AS stadium,
    COALESCE(m.city_id, s.city_id) AS city_id, ci.name AS city, ci.state AS state,
    m.country_iso2, co.name_pt AS country, co.continent AS continent, m.country_status,
    m.attendance,
    m.referee_id, r.name AS referee, m.referee_status,
    m.flu_kit_id, k.name AS kit, k.category AS kit_category, m.kit_status,
    m.flu_coach_id, p.name AS coach, m.opp_coach,
    m.reliability, m.verification_status
FROM matches m
JOIN teams o ON o.id = m.opponent_id
JOIN teams h ON h.id = m.home_team_id
JOIN teams a ON a.id = m.away_team_id
LEFT JOIN competitions c ON c.id = m.competition_id
LEFT JOIN competition_editions e ON e.id = m.edition_id
LEFT JOIN stadiums s ON s.id = m.stadium_id
LEFT JOIN cities ci ON ci.id = COALESCE(m.city_id, s.city_id)
LEFT JOIN countries co ON co.iso2 = m.country_iso2
LEFT JOIN referees r ON r.id = m.referee_id
LEFT JOIN kits k ON k.id = m.flu_kit_id
LEFT JOIN people p ON p.id = m.flu_coach_id;
