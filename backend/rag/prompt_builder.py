try:
    from rag.grounding import GROUNDING_SUFFIX
except ImportError:  # when run with rag/ directly on sys.path
    from grounding import GROUNDING_SUFFIX

SYSTEM_PROMPT = """You are OneTap AI, a Radiant-level Valorant coach with
expertise in mechanical skill development, strategic positioning, economy
management, and competitive mental frameworks.

Your coaching style:
- Be SPECIFIC, not generic. Reference exact stats and situations.
- Prescribe ACTIONABLE fixes, not vague advice.
- Calibrate advice to the player's RANK and HARDWARE.
- Acknowledge what the player does WELL before addressing weaknesses.
- Use coaching terminology precisely (peek, jiggle, counter-strafe, etc.)
- When suggesting aim drills, calibrate to the player's exact eDPI.
- NEVER ask the player for match IDs, round logs, VOD links, tracker
  exports, or screenshots — match data is ingested automatically. If data
  for a specific match is missing, say so plainly and answer from whatever
  stats you do have.
- When a "Match Under Review" section is present, analyze it round by round:
  economy discipline (bad force-buys, eco management), opening duel outcomes,
  death timings (early deaths = over-aggression, late = clutch situations),
  side-specific patterns (attack vs defense), and momentum swings (lost
  streaks after won rounds). Cite specific round numbers as evidence.
- Judge performance against the OPPONENTS FACED, never against raw numbers
  alone. When an "Opponent Context" section is present:
  - Never call a lower ACS a decline without first checking whether the
    player was facing stronger opponents. Say which it was.
  - After a promotion, expect a dip: the player is now the weakest-ranked
    in lobbies they used to top. Frame it as adjusting to a harder bracket,
    not as regression, and do not tell them they are playing worse.
  - Deaths to clearly higher-ranked opponents are lobby context, not a flaw
    to fix. Deaths to LOWER-ranked opponents are the real signal worth
    coaching — that is where to focus.
  - Ranked lobbies are usually within one rank step, so small differences in
    average lobby rank mean nothing. Only draw conclusions from a clearly
    lopsided gap or from one specific much-stronger opponent.
  - Never invent an "expected ACS" for a rank. Use only the numbers given.

You have access to the player's detailed analysis and relevant coaching
knowledge. Ground your responses in this data — do not hallucinate
statistics or fabricate scenarios."""

def _format_match_context(match: dict, rounds: list[dict]) -> str:
    """Render one match's round-by-round data as a compact prompt section."""
    header = (
        f"\n## Match Under Review — {match.get('map', '?')} "
        f"[{match.get('game_mode', 'Unknown')}] "
        f"({'WIN' if match.get('won') else 'LOSS'} "
        f"{match.get('team_score', 0)}-{match.get('enemy_score', 0)})\n"
        f"- **Played**: {match.get('started_at', '?')}\n"
        f"- **Agent**: {match.get('agent', '?')} | **ACS**: {match.get('acs', 0)} | "
        f"**K/D/A**: {match.get('kills', 0)}/{match.get('deaths', 0)}/{match.get('assists', 0)} | "
        f"**HS%**: {match.get('headshot_pct', 0)}%\n\n"
        "### Round-by-Round (player's perspective)\n"
        "| Rd | Side | Result | K/D/A | Dmg | Buy | Opening duel | Notes |\n"
        "|----|------|--------|-------|-----|-----|--------------|-------|\n"
    )
    lines = []
    for r in rounds:
        notes = []
        if r.get("planted_bomb"):
            notes.append("planted")
        if r.get("defused_bomb"):
            notes.append("defused")
        for k in r.get("kill_details", []):
            notes.append(f"kill w/ {k['weapon']}{' (HS)' if k['headshot'] else ''} @{k['at_sec']}s")
        d = r.get("death_detail")
        if d:
            notes.append(f"died to {d['weapon']}{' (HS)' if d['headshot'] else ''} @{d['at_sec']}s")
        if r.get("was_afk"):
            notes.append("AFK")
        lines.append(
            f"| {r['round']} | {r['side']} | {'won' if r['won'] else 'LOST'} ({r['result']}) "
            f"| {r['kills']}/{r['deaths']}/{r['assists']} | {r['damage_dealt']} "
            f"| {r['economy_class']} ({r['loadout_value']}) "
            f"| {r['opening_duel'] or '-'} | {'; '.join(notes) or '-'} |"
        )
    return header + "\n".join(lines) + "\n"


def _format_opponent_context(
    lobby: list[dict] | None,
    transition: dict | None,
    duels: dict | None,
) -> str:
    """Render who the player actually faced, so the coach can separate
    "the lobby got harder" from "you played worse"."""
    if not (lobby or transition or duels):
        return ""

    out = "\n## Opponent Context\n"

    if lobby:
        recent = lobby[-5:]
        avg_delta = sum(m["lobby_delta"] for m in lobby) / len(lobby)
        harder = sum(1 for m in lobby if m["lobby_delta"] >= 1)
        out += (
            f"- **Current rank**: {lobby[-1]['player_tier_name']}\n"
            f"- **Lobby difficulty (last {len(lobby)})**: enemy teams averaged "
            f"{avg_delta:+.2f} rank steps vs the player "
            f"({harder} clearly harder than their own rank). "
            f"One step = one subtier; ranked lobbies are normally within ±1, "
            f"so treat small values as even.\n"
            "\n| Match | Player rank | Enemy avg (steps) | Toughest enemy | ACS |\n"
            "|-------|-------------|-------------------|----------------|-----|\n"
        )
        for m in recent:
            out += (
                f"| {m['map']} | {m['player_tier_name']} | {m['lobby_delta']:+.2f} "
                f"| {m['enemy_max_tier_name']} ({m['toughest_enemy_edge']:+d}) | {m['acs']} |\n"
            )

    if transition:
        d = transition["direction"]
        out += (
            f"\n- **Recent {d}**: {transition['from_tier_name']} → "
            f"{transition['to_tier_name']}, {transition['matches_since']} matches ago. "
            f"ACS {transition['acs_before']} → {transition['acs_after']}, "
            f"K/D {transition['kd_before']} → {transition['kd_after']}.\n"
        )
        if transition.get("calibrating") and d == "promotion":
            out += (
                "  Still adjusting to the new bracket — a dip here is expected, "
                "because everyone in these lobbies is stronger than before. "
                "Do NOT describe this as the player getting worse.\n"
            )

    if duels:
        k, dth = duels["kills"], duels["deaths"]
        out += (
            f"\n- **Duels (last {duels['matches_covered']} matches)**: "
            f"killed {k['vs_stronger']} higher-ranked / {k['vs_even']} even / "
            f"{k['vs_weaker']} lower-ranked; "
            f"died to {dth['to_stronger']} higher-ranked / {dth['to_even']} even / "
            f"{dth['to_weaker']} lower-ranked.\n"
        )
        if duels.get("deaths_to_weaker_pct") is not None:
            out += (
                f"  {duels['deaths_to_weaker_pct']}% of deaths came from "
                f"LOWER-ranked opponents — this is the coachable part.\n"
            )
        nem = duels.get("nemesis")
        if nem:
            out += (
                f"  Single opponent {nem['name']} caused {nem['deaths']} deaths "
                f"({nem['share_pct']}% of all deaths, {nem['tier_edge']:+d} rank steps).\n"
            )

    return out


def build_coaching_prompt(
    player_profile: dict,
    retrieved_chunks: list[dict],
    user_question: str,
    match_context: dict | None = None,
) -> list[dict]:
    """Assemble the full prompt with player context and retrieved knowledge.

    match_context, when provided, is {"match": <find_recent_match dict>,
    "rounds": <get_match_rounds list>} and adds a round-by-round section so
    the model can answer questions about a specific match.
    """

    # Format player data
    # Calculate utility death percentage safely
    u_deaths = player_profile.get('utility_deaths_count', 0)
    g_deaths = player_profile.get('gun_deaths_count', 0)
    total_d = u_deaths + g_deaths
    util_pct = (u_deaths / max(1, total_d)) * 100
    util_list_str = ", ".join(f"{d['ability']} ({d['deaths']} deaths)" for d in player_profile.get('utility_deaths', []))

    player_context = f"""
## Player Profile
- **Riot ID**: {player_profile.get('game_name', '')}#{player_profile.get('tag_line', '')}
- **Main Agent**: {player_profile.get('main_agent', '')}
- **Overall ACS**: {player_profile.get('avg_acs', 0):.1f}
- **Headshot %**: {player_profile.get('headshot_pct', 0):.1f}%
- **Opening Duel Win Rate**: {player_profile.get('opening_duel_wr', 0):.1f}%
- **Zero-Damage Death %**: {player_profile.get('zero_dmg_death_pct', 0):.1f}%

## Strategic Matchups & Utility Deaths
- **Deaths to Duelist killers**: {player_profile.get('killer_roles', {}).get('Duelist', 0)}
- **Deaths to Initiator killers**: {player_profile.get('killer_roles', {}).get('Initiator', 0)}
- **Deaths to Sentinel killers**: {player_profile.get('killer_roles', {}).get('Sentinel', 0)}
- **Deaths to Controller killers**: {player_profile.get('killer_roles', {}).get('Controller', 0)}
- **Total deaths by Utilities/Abilities**: {u_deaths} ({util_pct:.1f}% of all deaths)
- **Top utility/ability causes of death**: {util_list_str if util_list_str else "None recorded"}

## Identified Issues
{chr(10).join(f'- {issue}' for issue in player_profile.get('issues', []))}
"""

    # Optional sections — only rendered when the caller actually computed
    # them. Emitting defaults here would show the LLM fake zeros and violate
    # the grounding rules.
    if 'acs_cv' in player_profile:
        player_context += f"""
## ACS Variance (Feast-or-Famine Score)
- **CV Score**: {player_profile.get('acs_cv', 0):.3f} (>0.5 = feast-or-famine)
- **Score Range**: {player_profile.get('score_range', 'N/A')}
"""
    if 'wide_swing_pct' in player_profile:
        player_context += f"""
## Peek Analysis (Last 20 Matches)
- **Wide Swings**: {player_profile.get('wide_swing_pct', 0):.1f}%
- **Crossfire Deaths**: {player_profile.get('crossfire_death_pct', 0):.1f}%
- **Tight Peeks**: {player_profile.get('tight_peek_pct', 0):.1f}%
"""
    if 'tilt_probability' in player_profile:
        player_context += f"""
## Tilt Status
- **Session Tilt Probability**: {player_profile.get('tilt_probability', 0):.2f}
- **Session ACS Trend**: {player_profile.get('acs_slope', 'stable')}
"""

    patterns = player_profile.get("round_patterns")
    if patterns:
        def _pct(v):
            return f"{v:.1f}%" if v is not None else "no data"

        pistol = patterns.get("pistol", {})
        post = patterns.get("post_pistol", {})
        momentum = patterns.get("momentum", {})
        atk = patterns.get("sides", {}).get("attack", {})
        dfn = patterns.get("sides", {}).get("defense", {})
        player_context += f"""
## Round Patterns (last {patterns.get('matches_covered', 0)} matches, {patterns.get('total_rounds', 0)} rounds)
- **Pistol rounds**: {_pct(pistol.get('win_pct'))} win rate over {pistol.get('rounds', 0)} pistols ({pistol.get('avg_kills', 0)} K / {pistol.get('avg_deaths', 0)} D per pistol)
- **Round after winning pistol**: {_pct(post.get('after_win_pct'))} | **after losing pistol**: {_pct(post.get('after_loss_pct'))}
- **Momentum**: {_pct(momentum.get('after_won_round_pct'))} win rate after a won round vs {_pct(momentum.get('after_lost_round_pct'))} after a lost round
- **Attack**: {_pct(atk.get('win_pct'))} WR, {_pct(atk.get('early_death_pct'))} early-death rate, opening duels {_pct(atk.get('opening_duel_win_pct'))} ({atk.get('opening_duel_attempts', 0)} taken)
- **Defense**: {_pct(dfn.get('win_pct'))} WR, {_pct(dfn.get('early_death_pct'))} early-death rate, opening duels {_pct(dfn.get('opening_duel_win_pct'))} ({dfn.get('opening_duel_attempts', 0)} taken)
"""

    opponents = _format_opponent_context(
        player_profile.get("lobby_context"),
        player_profile.get("rank_transition"),
        player_profile.get("duel_strength"),
    )
    if opponents:
        player_context += opponents

    otr = player_profile.get("otr")
    if otr:
        pillars = otr.get("pillars", {})
        mission = otr.get("mission") or {}
        prev = otr.get("otr_previous")
        player_context += f"""
## OneTap Rating (lobby-relative performance, 50 = lobby average)
- **Current OTR (last 10 matches)**: {otr.get('otr')}{f" (previous 10: {prev}, trend: {otr.get('trend')})" if prev is not None else ""}
- **Pillars (0-100)**: damage {pillars.get('damage')}, survival {pillars.get('survival')}, impact {pillars.get('impact')}, precision {pillars.get('precision')}
- **Weakest pillar**: {otr.get('weakest_pillar')}
- **Active mission**: {mission.get('title', 'none')} — {mission.get('goal', '')}
OTR compares the player to the other 9 in each of their own lobbies, so it is
already rank- and opponent-adjusted; trend moves inside ±3 points are noise.
When coaching, anchor advice to the weakest pillar and the active mission.
"""

    if match_context:
        if match_context.get("rounds"):
            player_context += _format_match_context(
                match_context.get("match", {}), match_context["rounds"]
            )
        else:
            where = f" on {match_context['requested_map']}" if match_context.get("requested_map") else ""
            player_context += (
                f"\n## Match Under Review\n"
                f"The player asked about a specific match{where}, but there are no "
                f"matches{where} in their synced history. Say so plainly and suggest "
                f"they play (or re-analyze) so the match gets picked up — do NOT ask "
                f"for match IDs, logs, or screenshots; data arrives automatically.\n"
            )

    # Format retrieved knowledge
    knowledge_context = "## Relevant Coaching Knowledge\n\n"
    for i, chunk in enumerate(retrieved_chunks, 1):
        source = chunk.get('source', 'Unknown')
        knowledge_context += f"### Source {i} [{source}]\n{chunk.get('content', '')}\n\n"

    return [
        {"role": "system", "content": SYSTEM_PROMPT + GROUNDING_SUFFIX},
        {"role": "user", "content": (
            f"{player_context}\n\n"
            f"{knowledge_context}\n\n"
            f"---\n\n"
            f"## Player's Question\n{user_question}"
        )},
    ]
