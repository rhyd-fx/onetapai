-- ================================================================
-- OneTap AI — MariaDB Schema
-- Engine: InnoDB | Charset: utf8mb4 | Collation: utf8mb4_unicode_ci
-- ================================================================

CREATE DATABASE IF NOT EXISTS onetapai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE onetapai;

-- ----------------------------------------------------------------
-- Core Entity Tables
-- ----------------------------------------------------------------

CREATE TABLE players (
    puuid           CHAR(78)        NOT NULL,
    game_name       VARCHAR(16)     NOT NULL,
    tag_line        VARCHAR(5)      NOT NULL,
    region          VARCHAR(10)     NOT NULL DEFAULT 'na',
    first_seen      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_synced     TIMESTAMP       NULL,
    PRIMARY KEY (puuid),
    INDEX idx_players_gamename (game_name, tag_line)
) ENGINE=InnoDB;

CREATE TABLE matches (
    match_id        VARCHAR(36)     NOT NULL,
    map_id          VARCHAR(20)     NOT NULL,
    game_mode       VARCHAR(20)     NOT NULL,
    queue_id        VARCHAR(20)     NULL,
    game_length_ms  INT UNSIGNED    NOT NULL,
    started_at      TIMESTAMP       NOT NULL,
    season_id       VARCHAR(36)     NULL,   -- Henrik returns a 36-char season UUID
    rounds_played   TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (match_id),
    INDEX idx_matches_started (started_at),
    INDEX idx_matches_map (map_id, started_at)
) ENGINE=InnoDB;

CREATE TABLE player_match_stats (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    match_id        VARCHAR(36)     NOT NULL,
    puuid           CHAR(78)        NOT NULL,
    team_id         VARCHAR(10)     NOT NULL,
    agent_id        VARCHAR(20)     NOT NULL,
    -- Match-level aggregates (derived, but cached for fast reads)
    total_score     INT UNSIGNED    NOT NULL DEFAULT 0,
    total_rounds    TINYINT UNSIGNED NOT NULL DEFAULT 0,
    acs             FLOAT           GENERATED ALWAYS AS (
                        CASE WHEN total_rounds > 0
                             THEN total_score / total_rounds
                             ELSE 0 END
                    ) STORED,
    total_kills     SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    total_deaths    SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    total_assists   SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    headshot_pct    FLOAT           NULL,
    bodyshot_pct    FLOAT           NULL,
    legshot_pct     FLOAT           NULL,
    won             BOOLEAN         NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_match_player (match_id, puuid),
    INDEX idx_pms_puuid_time (puuid),
    CONSTRAINT fk_pms_match FOREIGN KEY (match_id) REFERENCES matches(match_id),
    CONSTRAINT fk_pms_player FOREIGN KEY (puuid) REFERENCES players(puuid)
) ENGINE=InnoDB;

CREATE TABLE rounds (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    match_id        VARCHAR(36)     NOT NULL,
    round_num       TINYINT UNSIGNED NOT NULL,
    round_result    VARCHAR(20)     NOT NULL,
    round_result_code VARCHAR(20)   NULL,
    winning_team    VARCHAR(10)     NOT NULL,
    bomb_planter    CHAR(78)        NULL,
    bomb_defuser    CHAR(78)        NULL,
    plant_time_ms   INT UNSIGNED    NULL,
    defuse_time_ms  INT UNSIGNED    NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_match_round (match_id, round_num),
    INDEX idx_rounds_match (match_id),
    CONSTRAINT fk_rounds_match FOREIGN KEY (match_id) REFERENCES matches(match_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------
-- Spatial & Event Tables (Core of the Analysis Engine)
-- ----------------------------------------------------------------

CREATE TABLE kill_events (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    round_id            BIGINT UNSIGNED NOT NULL,
    killer_puuid        CHAR(78)        NOT NULL,
    victim_puuid        CHAR(78)        NOT NULL,
    time_in_round_ms    INT UNSIGNED    NOT NULL,
    -- Spatial coordinates: raw Unreal-engine world units, LARGE SIGNED values
    -- (observed range roughly -9500..+8300, NOT a normalized 0-1024 grid).
    -- Normalize per-map at query/analysis time using per-map coordinate bounds.
    killer_x            FLOAT           NOT NULL,
    killer_y            FLOAT           NOT NULL,
    victim_x            FLOAT           NOT NULL,
    victim_y            FLOAT           NOT NULL,
    -- Engagement metadata
    weapon              VARCHAR(30)     NOT NULL,
    finishing_damage_type VARCHAR(10)   NOT NULL COMMENT 'headshot|bodyshot|legshot',
    is_opening_kill     BOOLEAN         NOT NULL DEFAULT FALSE,
    assistants_count    TINYINT UNSIGNED NOT NULL DEFAULT 0,
    -- Derived: Euclidean engagement distance
    engagement_distance FLOAT           GENERATED ALWAYS AS (
                            SQRT(
                                POW(killer_x - victim_x, 2) +
                                POW(killer_y - victim_y, 2)
                            )
                        ) STORED,
    -- Derived: Engagement angle (radians from X-axis)
    engagement_angle    FLOAT           GENERATED ALWAYS AS (
                            ATAN2(victim_y - killer_y, victim_x - killer_x)
                        ) STORED,
    PRIMARY KEY (id),
    INDEX idx_ke_round (round_id),
    INDEX idx_ke_killer (killer_puuid, time_in_round_ms),
    INDEX idx_ke_victim (victim_puuid),
    INDEX idx_ke_spatial_killer (killer_x, killer_y),
    INDEX idx_ke_spatial_victim (victim_x, victim_y),
    INDEX idx_ke_opening (is_opening_kill, killer_puuid),
    CONSTRAINT fk_ke_round FOREIGN KEY (round_id) REFERENCES rounds(id)
) ENGINE=InnoDB;

CREATE TABLE player_round_stats (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    round_id            BIGINT UNSIGNED NOT NULL,
    puuid               CHAR(78)        NOT NULL,
    agent_id            VARCHAR(20)     NOT NULL,
    team_id             VARCHAR(10)     NOT NULL,
    score               INT UNSIGNED    NOT NULL DEFAULT 0,
    kills               TINYINT UNSIGNED NOT NULL DEFAULT 0,
    deaths              TINYINT UNSIGNED NOT NULL DEFAULT 0,
    assists             TINYINT UNSIGNED NOT NULL DEFAULT 0,
    damage_dealt        INT UNSIGNED    NOT NULL DEFAULT 0,
    damage_received     INT UNSIGNED    NOT NULL DEFAULT 0,
    economy_loadout_value INT UNSIGNED  NOT NULL DEFAULT 0,
    economy_remaining   INT UNSIGNED    NOT NULL DEFAULT 0,
    economy_spent       INT UNSIGNED    NOT NULL DEFAULT 0,
    was_afk             BOOLEAN         NOT NULL DEFAULT FALSE,
    was_penalized       BOOLEAN         NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    UNIQUE KEY uk_round_player (round_id, puuid),
    INDEX idx_prs_puuid (puuid, round_id),
    INDEX idx_prs_agent (agent_id, puuid),
    INDEX idx_prs_economy (economy_loadout_value),
    CONSTRAINT fk_prs_round FOREIGN KEY (round_id) REFERENCES rounds(id),
    CONSTRAINT fk_prs_player FOREIGN KEY (puuid) REFERENCES players(puuid)
) ENGINE=InnoDB;

CREATE TABLE player_locations (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    round_id            BIGINT UNSIGNED NOT NULL,
    puuid               CHAR(78)        NOT NULL,
    x                   FLOAT           NOT NULL,
    y                   FLOAT           NOT NULL,
    view_radians        FLOAT           NOT NULL COMMENT 'Yaw direction player is facing',
    capture_time_ms     INT UNSIGNED    NOT NULL COMMENT 'Timestamp within the round',
    PRIMARY KEY (id),
    INDEX idx_pl_round_player (round_id, puuid),
    INDEX idx_pl_spatial (x, y),
    CONSTRAINT fk_pl_round FOREIGN KEY (round_id) REFERENCES rounds(id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------
-- Player Configuration & Hardware
-- ----------------------------------------------------------------

CREATE TABLE player_hardware_profiles (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    puuid               CHAR(78)        NOT NULL,
    mouse_dpi           INT UNSIGNED    NOT NULL DEFAULT 800,
    in_game_sens        FLOAT           NOT NULL DEFAULT 0.5,
    edpi                FLOAT           GENERATED ALWAYS AS (mouse_dpi * in_game_sens) STORED,
    mouse_model         VARCHAR(50)     NULL,
    monitor_resolution  VARCHAR(20)     NULL DEFAULT '1920x1080',
    monitor_refresh_rate INT UNSIGNED   NULL DEFAULT 144,
    zoom_sens_multiplier FLOAT          NOT NULL DEFAULT 1.0,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_hw_puuid (puuid),
    CONSTRAINT fk_hw_player FOREIGN KEY (puuid) REFERENCES players(puuid)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------
-- Coaching & Session Tracking
-- ----------------------------------------------------------------

CREATE TABLE coaching_sessions (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    puuid               CHAR(78)        NOT NULL,
    session_start       TIMESTAMP       NOT NULL,
    session_end         TIMESTAMP       NULL,
    focus_area          VARCHAR(30)     NULL COMMENT 'aim|positioning|economy|mental|utility',
    coaching_summary    TEXT            NULL,
    action_items_json   JSON            NULL,
    matches_analyzed    JSON            NULL COMMENT 'Array of match_ids covered',
    PRIMARY KEY (id),
    INDEX idx_cs_puuid (puuid, session_start),
    CONSTRAINT fk_cs_player FOREIGN KEY (puuid) REFERENCES players(puuid)
) ENGINE=InnoDB;

CREATE TABLE player_sessions (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    puuid               CHAR(78)        NOT NULL,
    session_date        DATE            NOT NULL,
    first_match_at      TIMESTAMP       NOT NULL,
    last_match_at       TIMESTAMP       NOT NULL,
    match_count         TINYINT UNSIGNED NOT NULL,
    -- Session-level ACS trajectory for tilt detection
    acs_first_match     FLOAT           NULL,
    acs_last_match      FLOAT           NULL,
    acs_trend_slope     FLOAT           NULL COMMENT 'Linear regression slope across session',
    acs_std_dev         FLOAT           NULL,
    avg_queue_gap_min   FLOAT           NULL COMMENT 'Avg minutes between matches',
    tilt_probability    FLOAT           NULL COMMENT '0.0–1.0 computed tilt score',
    PRIMARY KEY (id),
    UNIQUE KEY uk_session (puuid, session_date),
    INDEX idx_ps_tilt (puuid, tilt_probability),
    CONSTRAINT fk_ps_player FOREIGN KEY (puuid) REFERENCES players(puuid)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------
-- Coaching Feedback (thumbs up/down → knowledge-gap signal)
-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS coaching_feedback (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    puuid               CHAR(78)        NULL,
    question            TEXT            NOT NULL,
    answer_excerpt      TEXT            NULL,
    rating              TINYINT         NOT NULL COMMENT '1 = thumbs up, -1 = thumbs down',
    sources_json        JSON            NULL COMMENT 'Retrieved sources for gap analysis',
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_cf_rating (rating, created_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------
-- Economy Classification View
-- ----------------------------------------------------------------

CREATE OR REPLACE VIEW v_round_economy_class AS
SELECT
    prs.id AS prs_id,
    prs.round_id,
    prs.puuid,
    prs.economy_loadout_value,
    CASE
        WHEN prs.economy_loadout_value < 2000  THEN 'eco'
        WHEN prs.economy_loadout_value < 3900  THEN 'half_buy'
        WHEN prs.economy_loadout_value < 4500  THEN 'force_buy'
        ELSE 'full_buy'
    END AS economy_class,
    prs.score,
    prs.kills,
    prs.deaths,
    prs.damage_dealt
FROM player_round_stats prs;

-- ----------------------------------------------------------------
-- ACS Variance Analysis View (Feast-or-Famine Detection)
-- ----------------------------------------------------------------

CREATE OR REPLACE VIEW v_player_acs_variance AS
SELECT
    prs.puuid,
    prs.agent_id,
    r.match_id,
    COUNT(*)                    AS rounds_played,
    AVG(prs.score)              AS avg_round_score,
    STDDEV_POP(prs.score)       AS score_stddev,
    VARIANCE(prs.score)         AS score_variance,
    -- Coefficient of variation: high = feast-or-famine
    CASE
        WHEN AVG(prs.score) > 0
        THEN STDDEV_POP(prs.score) / AVG(prs.score)
        ELSE 0
    END                         AS cv_score,
    MAX(prs.score)              AS max_round_score,
    MIN(prs.score)              AS min_round_score,
    MAX(prs.score) - MIN(prs.score) AS score_range
FROM player_round_stats prs
JOIN rounds r ON prs.round_id = r.id
GROUP BY prs.puuid, prs.agent_id, r.match_id;

-- ----------------------------------------------------------------
-- Opening Duel Performance View
-- ----------------------------------------------------------------

CREATE OR REPLACE VIEW v_opening_duel_stats AS
SELECT
    ke.killer_puuid                                         AS puuid,
    'kill'                                                  AS outcome,
    ke.weapon,
    ke.finishing_damage_type,
    ke.engagement_distance,
    ke.killer_x                                             AS player_x,
    ke.killer_y                                             AS player_y,
    ke.time_in_round_ms,
    r.match_id,
    r.round_num
FROM kill_events ke
JOIN rounds r ON ke.round_id = r.id
WHERE ke.is_opening_kill = TRUE

UNION ALL

SELECT
    ke.victim_puuid                                         AS puuid,
    'death'                                                 AS outcome,
    ke.weapon,
    ke.finishing_damage_type,
    ke.engagement_distance,
    ke.victim_x                                             AS player_x,
    ke.victim_y                                             AS player_y,
    ke.time_in_round_ms,
    r.match_id,
    r.round_num
FROM kill_events ke
JOIN rounds r ON ke.round_id = r.id
WHERE ke.is_opening_kill = TRUE;
