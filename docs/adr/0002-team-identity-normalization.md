# ADR 0002 — Team identity normalization + round-outcome correctness

- **Status:** Accepted & implemented (2026-07-06)
- **Area:** ingestion / analysis
- **Unblocks:** Attack/Defense splits, win/loss streaks, clutch stats (ADR-0003 batch)

## Context

Henrik returns team identifiers two ways:

- **Standard matches:** `"Red"` / `"Blue"`.
- **Premier / custom matches:** arbitrary team **UUIDs** (e.g. `73b09c0e-…`), and
  their `teams.red/blue.has_won` is **`null`**.

The old ETL stored the raw value into `player_match_stats.team_id`,
`player_round_stats.team_id`, and `rounds.winning_team`, and computed `won` via
`teams[player_team.lower()].has_won`. Consequences:

1. Team columns held a mix of `Red`/`Blue` **and** UUIDs → any
   `team_id = winning_team` join was silently wrong for UUID matches
   (4,656 player-match rows, 388 matches).
2. For UUID matches `has_won` is `null`, so `won` was silently `False` for
   everyone in those matches.

## Decision

Normalize team identity at ingest and derive the winner robustly:

- Map every raw team id → canonical **`Red`/`Blue`** (first-seen order for UUID
  matches; identity for standard matches). Applied to all three columns.
- Determine the winner from **round-win counts** (`max` over
  `rounds[].winning_team`), which works for every match type, with a
  `teams.has_won` fallback. `won = (player_canon_team == winning_team)`.

Implemented in `ingestion/etl.py::_build_team_normalizer` (replaces
`_determine_won`). A one-time repair (`ingestion/repair_teams.py`) deletes and
re-ingests affected matches from archived raw JSON.

## Outcome (verified)

- Bad team rows: **4,656 → 132** (the 132 are 11 premier matches whose raw JSON
  was never archived — unrepairable, see below).
- Per-match sanity: a competitive match now shows exactly 5 won / 5 lost per team.
- **Won% by mode is now correct:** Competitive **49.3%** (≈50%, as required),
  Swiftplay/Unrated/TDM 50.0%. The overall 62% is entirely **Deathmatch (85.7%)**
  — expected, because DM is a free-for-all with no meaningful team/winner.

## Consequence for downstream features (important)

Team- and round-outcome-based stats **must exclude non-team modes** (Deathmatch,
and treat TDM/Escalation with care). Filter `matches.game_mode` to team modes
(`Competitive`, `Unrated`, `Swiftplay`, `Premier`, `Spike Rush`) before computing
Attack/Defense splits, win/loss streaks, or clutch rates. See glossary: **team mode**.

## Residual / accepted risk

- **11 premier matches (132 rows)** keep UUID team ids because their raw JSON was
  not archived. Features that join on team must filter `team_id IN ('Red','Blue')`
  (or exclude those match_ids). Low impact (<1% of rows) and self-healing: if those
  matches are re-fetched and archived, re-running `repair_teams` fixes them.
- Going forward, all newly ingested matches are normalized at write time, so the
  problem does not recur.
