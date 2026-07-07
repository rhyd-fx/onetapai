# OneTap AI — Domain Glossary

Ubiquitous language for the coaching domain. Terms are how we name things in
code, DB, API, and UI. Keep this in sync when a definition changes.

---

### loadout_value
Credits a player spent on their loadout (weapons + armor + abilities) **at the
start of a round**. Source: Henrik `rounds[].player_stats[].economy.loadout_value`;
stored as `player_round_stats.economy_loadout_value`. It is a *spend snapshot*,
not a per-round budget. Range observed: 0–7500. ~6% of rows are 0 (pistol/eco or
missing). Basis for **buy tier**.

### buy tier
Bucketing of a round by `loadout_value`, matching the `v_round_economy_class` view:
- **eco** `< 2000` — saving; pistol + light shields.
- **half-buy** `2000–3899` — SMGs / partial rifle.
- **force(-buy)** `3900–4499` — near-full spend on a round you "should" save.
- **full-buy** `≥ 4500` — rifle + full shields + util.
One canonical definition; do not redefine thresholds per feature.

### Economy Impact (metric)
The player's **ACS split across buy tiers** (eco/half/force/full). Chosen over
round-win%-by-tier because it isolates individual output and is not confounded by
the 5v5 team result (see ADR 0001). Drives the "Tactical & Economic" panel label.

### ACS (Average Combat Score)
Per-round combat score averaged over rounds. Stored per round as
`player_round_stats.score`; `player_match_stats.acs` is the match-level generated
average. The core performance signal across the app (tilt, economy, consistency).

### buy discipline (deferred)
Whether a player's buy was *coordinated with their team* (bought/saved together)
vs. a lone force/save. NOT yet modeled — requires all 5 teammates' per-round
economy. Deferred in ADR 0001.

### round outcome / winning_team
Which team won a round. Source: `rounds.winning_team`, normalized to canonical
`Red`/`Blue` at ingest. Compared against `player_round_stats.team_id` (also
canonical) to decide if a player won a round. Fixed in ADR-0002 — team ids used
to be a mix of `Red`/`Blue` and premier-match UUIDs. Residual: 11 un-archived
premier matches still hold UUIDs; filter `team_id IN ('Red','Blue')` on joins.

### team mode
A game mode with two opposing teams and a meaningful winner: Competitive,
Unrated, Swiftplay, Premier, Spike Rush. **Deathmatch is NOT a team mode** (free
-for-all; its `won`/`winning_team` are meaningless — 85.7% "won" artifact). All
team/round-outcome features (Attack/Defense split, win streaks, clutch) must
filter `matches.game_mode` to team modes. See ADR-0002.

### won
Whether a player's team won the match. `player_match_stats.won`, computed as
`player_canon_team == match_winner`, where the winner is the team with the most
round wins (robust for premier/UUID matches where `teams.has_won` is null).

### tier_id / tier_name
The player's competitive rank in that match. `player_match_stats.tier_id`
(numeric, e.g. 23) and `tier_name` (e.g. "Ascendant 3"), from Henrik
`all_players[].currenttier` / `currenttier_patched`. 99.3% populated. Basis for
the **rank-progression timeline**.

### ADR (Average Damage per Round)
Mean `player_round_stats.damage_dealt` over a player's rounds (≈144 typical). The
core raw performance metric; distinct from ACS (which weights kills/assists).

### FK / FD (First Kill / First Death)
Opening-duel outcomes. `kill_events.is_opening_kill = TRUE` with the player as
`killer_puuid` (first kill) or `victim_puuid` (first death). Surfaced in
`get_telemetry` as `first_kills`, `first_deaths`, `fk_fd_diff` (FK−FD, signed
entry-impact) and `opening_duel_win_pct`. Does not require the team-mode filter
(duel-level, not round-outcome). Rendered as the "First Duels (FK/FD)" tile.

### side bias (Attack vs Defense)
`get_side_bias` splits a player's rounds into Attack/Defense by round number and
canonical team, reporting per-side win% and early-defense death%. **Correctness
depends on ADR-0002** (canonical Red/Blue + correct winner) — it was silently
wrong for premier/UUID matches before the team-normalization fix. Caveat: the
round-number→side mapping assumes Red attacks first half; a rare per-match
convention mismatch would swap the two, but aggregate bias is directionally
sound.

### buy tier ACS (small-sample caveat)
A tier's ACS is only stable with enough rounds in it (rule of thumb ≥ ~5–8).
Below that, treat the tier as "insufficient data" rather than coaching on it.
