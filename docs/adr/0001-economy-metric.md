# ADR 0001 — Economy metric for the "Tactical & Economic" panel

- **Status:** Proposed (grilling session, 2026-07-06)
- **Context owner:** dashboard / analysis
- **Supersedes:** the hardcoded `"Economy": "Data Incoming"` placeholder in `viewModel.ts`

## Context

The dashboard's "Tactical & Economic" deep-dive card shows a hardcoded
`Economy: Data Incoming`. This is misleading: we **do** ingest per-round economy
(`player_round_stats.economy_loadout_value`, from Henrik
`rounds[].player_stats[].economy.loadout_value`). 93.9% of rounds have a
non-zero value (6.1% are 0 — pistol/eco or missing). So the data exists; only a
metric definition and wiring are missing.

The question this ADR settles: **what economy metric is actually meaningful for a
solo-queue player, given only their own per-round loadout value and round data?**

## The finding that reframes the feature

Naive intuition: "economy efficiency = do you convert full-buys into wins/ACS?"
The data contradicts the premise. Buy-tier breakdown for a real player (CHINMAYA,
228 rounds):

| Buy tier (loadout creds)        | Rounds | Avg ACS | Win % |
|---------------------------------|-------:|--------:|------:|
| Eco (<2000)                     |   46   |   174   | 58.7  |
| Half-buy (2000–3899)            |   58   |   231   | 56.9  |
| Force (3900–4499)               |   34   |   167   | 55.9  |
| Full-buy (≥4500)                |   32   |   192   | 56.3  |

Two things jump out:

1. **ACS peaks on half-buys (231), not full-buys (192).** The player performs
   *worse* with a full loadout. A "full-buy conversion" metric would score this
   player as economy-weak, which is the wrong read — he's actually a strong
   underdog/scrappy player who underuses his rifle rounds.
2. **Round win % is nearly flat across tiers (55.9–58.7%).** For a *single*
   player, buy tier barely predicts round outcome — unsurprising, because a round
   is a 5v5 team result and one player's loadout is weakly correlated with it.

Conclusion: **individual round win% by buy tier is too noisy/team-confounded to
coach on. ACS-by-buy-tier is the signal** — it isolates the player's own output
and reveals *where their economy discipline actually helps or hurts*.

## Decision

Ship an **"Economy Impact" metric = the player's ACS split across buy tiers**,
surfaced as:

- A headline label derived from the split (e.g. *"Half-buy specialist"*,
  *"Full-buy underperformer"*, *"Balanced"*), replacing `Data Incoming`.
- The underlying eco/half/force/full ACS values available for a future stacked chart.

Buy-tier thresholds (creds), reused from the existing `v_round_economy_class` view
so the app has one definition:

- eco `< 2000`, half `2000–3899`, force `3900–4499`, full `≥ 4500`.

Coaching interpretation encoded in the view-model:

- `full_acs < half_acs` (by a margin) → **"Full-buy underperformer"**: you leave
  value on the table in the rounds you're best equipped to win.
- `eco_acs` unusually high → **"Eco threat"**: good at stealing low-buy rounds.
- roughly flat → **"Balanced economy"**.

## Why not the alternatives

- **Round win% by buy tier** — rejected as the *primary* metric: team-confounded
  and flat for individuals (evidence above). May still be shown as secondary.
- **"Buy discipline" (did you buy with your team / avoid forcing)** — rejected for
  now: requires the *team's* economy per round to know if a buy was coordinated or
  a lone force. We only reliably have the target player's loadout; teammates'
  per-round economy is present in the JSON but not modeled. Deferred (see open
  questions).
- **Credit-efficiency (damage per cred)** — rejected: `loadout_value` is spend on
  *guns+armor+util at round start*, not a per-round budget; ratio is not
  meaningful round-to-round and rewards eco rounds artificially.

## Consequences

- `get_economy_split(conn, puuid)` query returns `{eco, half, force, full}` ACS +
  round counts; `/analyze` includes it; `viewModel` derives the label.
- The `/api/v1/player/{id}/economy-impact` endpoint (currently 501) can be
  implemented from the same query.
- Small-sample caveat: with <~5 rounds in a tier, the tier ACS is unstable. The
  label logic must guard on minimum round counts or say "not enough data" per tier.

## Open questions (unresolved — need product input)

1. **Primary vs. secondary:** headline = ACS-by-tier label only, or also show
   round win% by tier as a secondary line despite its noise?
2. **Team economy / buy discipline:** worth modeling teammates' per-round economy
   to detect "you forced alone" / "you saved when team bought"? Higher ETL cost.
3. **Minimum-sample policy:** below N rounds in a tier, hide the tier, gray it, or
   widen to eco-vs-buy binary?

## Data-quality issue surfaced during grilling (must fix regardless)

`player_round_stats.team_id` and `rounds.winning_team` are stored
**inconsistently**: some rows use `Red`/`Blue`, others a team **UUID**
(`7f87ae5f-…`). Any round-outcome-by-player join (win% features, opening-duel
context) is silently wrong for the UUID rows. Tracked in the glossary under
**team_id**; needs an ETL normalization pass. This is the reason round win% must
not be trusted until fixed.
