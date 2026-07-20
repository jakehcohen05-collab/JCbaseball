-- Baseball Analysis Database Schema
-- A normalized relational schema for storing teams, players, games,
-- and per-game batting and pitching lines. Designed for SQLite.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Reference tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,
    abbrev      TEXT    NOT NULL UNIQUE,   -- e.g. 'NYY'
    name        TEXT    NOT NULL,          -- e.g. 'New York Yankees'
    league      TEXT    NOT NULL CHECK (league IN ('AL', 'NL')),
    division    TEXT    NOT NULL CHECK (division IN ('East', 'Central', 'West'))
);

CREATE TABLE IF NOT EXISTS players (
    player_id   INTEGER PRIMARY KEY,
    first_name  TEXT    NOT NULL,
    last_name   TEXT    NOT NULL,
    bats        TEXT    CHECK (bats IN ('L', 'R', 'S')),      -- left/right/switch
    throws      TEXT    CHECK (throws IN ('L', 'R')),
    primary_pos TEXT,                                          -- e.g. 'SS', 'SP'
    birth_date  TEXT,                                          -- ISO 8601
    team_id     INTEGER REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS games (
    game_id       INTEGER PRIMARY KEY,
    game_date     TEXT    NOT NULL,         -- ISO 8601
    season        INTEGER NOT NULL,
    home_team_id  INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id  INTEGER NOT NULL REFERENCES teams(team_id),
    home_score    INTEGER,
    away_score    INTEGER,
    CHECK (home_team_id <> away_team_id)
);

-- ---------------------------------------------------------------------------
-- Per-game stat lines. Season totals are derived by aggregation, so the
-- database stays the single source of truth for the raw events.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS batting_lines (
    id          INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    ab          INTEGER NOT NULL DEFAULT 0,   -- at-bats
    r           INTEGER NOT NULL DEFAULT 0,   -- runs
    h           INTEGER NOT NULL DEFAULT 0,   -- hits
    doubles     INTEGER NOT NULL DEFAULT 0,
    triples     INTEGER NOT NULL DEFAULT 0,
    hr          INTEGER NOT NULL DEFAULT 0,   -- home runs
    rbi         INTEGER NOT NULL DEFAULT 0,
    bb          INTEGER NOT NULL DEFAULT 0,   -- walks
    so          INTEGER NOT NULL DEFAULT 0,   -- strikeouts
    hbp         INTEGER NOT NULL DEFAULT 0,   -- hit by pitch
    sf          INTEGER NOT NULL DEFAULT 0,   -- sacrifice flies
    sb          INTEGER NOT NULL DEFAULT 0,   -- stolen bases
    cs          INTEGER NOT NULL DEFAULT 0,   -- caught stealing
    UNIQUE (game_id, player_id),
    CHECK (h <= ab OR ab = 0),
    CHECK (doubles + triples + hr <= h)
);

CREATE TABLE IF NOT EXISTS pitching_lines (
    id          INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    player_id   INTEGER NOT NULL REFERENCES players(player_id),
    team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    outs        INTEGER NOT NULL DEFAULT 0,   -- outs recorded (IP*3), avoids fractions
    bf          INTEGER NOT NULL DEFAULT 0,   -- batters faced
    h           INTEGER NOT NULL DEFAULT 0,   -- hits allowed
    r           INTEGER NOT NULL DEFAULT 0,   -- runs allowed
    er          INTEGER NOT NULL DEFAULT 0,   -- earned runs
    bb          INTEGER NOT NULL DEFAULT 0,   -- walks
    so          INTEGER NOT NULL DEFAULT 0,   -- strikeouts
    hr          INTEGER NOT NULL DEFAULT 0,   -- home runs allowed
    win         INTEGER NOT NULL DEFAULT 0 CHECK (win IN (0, 1)),
    loss        INTEGER NOT NULL DEFAULT 0 CHECK (loss IN (0, 1)),
    save        INTEGER NOT NULL DEFAULT 0 CHECK (save IN (0, 1)),
    started     INTEGER NOT NULL DEFAULT 0 CHECK (started IN (0, 1)),
    UNIQUE (game_id, player_id),
    CHECK (er <= r)
);

-- ---------------------------------------------------------------------------
-- Indexes for the common lookup paths.
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_batting_player  ON batting_lines(player_id);
CREATE INDEX IF NOT EXISTS idx_batting_game    ON batting_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_pitching_player ON pitching_lines(player_id);
CREATE INDEX IF NOT EXISTS idx_pitching_game   ON pitching_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_players_team     ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_games_season     ON games(season);

-- ---------------------------------------------------------------------------
-- Convenience views: season batting and pitching totals per player.
-- ---------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS batting_totals AS
SELECT
    b.player_id,
    g.season,
    COUNT(DISTINCT b.game_id)              AS g,
    SUM(b.ab)                              AS ab,
    SUM(b.r)                               AS r,
    SUM(b.h)                               AS h,
    SUM(b.doubles)                         AS doubles,
    SUM(b.triples)                         AS triples,
    SUM(b.hr)                              AS hr,
    SUM(b.rbi)                             AS rbi,
    SUM(b.bb)                              AS bb,
    SUM(b.so)                              AS so,
    SUM(b.hbp)                             AS hbp,
    SUM(b.sf)                              AS sf,
    SUM(b.sb)                              AS sb,
    SUM(b.cs)                              AS cs
FROM batting_lines b
JOIN games g ON g.game_id = b.game_id
GROUP BY b.player_id, g.season;

CREATE VIEW IF NOT EXISTS pitching_totals AS
SELECT
    p.player_id,
    g.season,
    COUNT(DISTINCT p.game_id)              AS g,
    SUM(p.started)                         AS gs,
    SUM(p.outs)                            AS outs,
    SUM(p.bf)                              AS bf,
    SUM(p.h)                               AS h,
    SUM(p.r)                               AS r,
    SUM(p.er)                              AS er,
    SUM(p.bb)                              AS bb,
    SUM(p.so)                              AS so,
    SUM(p.hr)                              AS hr,
    SUM(p.win)                             AS w,
    SUM(p.loss)                            AS l,
    SUM(p.save)                            AS sv
FROM pitching_lines p
JOIN games g ON g.game_id = p.game_id
GROUP BY p.player_id, g.season;
