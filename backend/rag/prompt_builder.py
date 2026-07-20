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
- When a "Match Under Review" section is present, analyze it round by round:
  economy discipline (bad force-buys, eco management), opening duel outcomes,
  death timings (early deaths = over-aggression, late = clutch situations),
  side-specific patterns (attack vs defense), and momentum swings (lost
  streaks after won rounds). Cite specific round numbers as evidence.

You have access to the player's detailed analysis and relevant coaching
knowledge. Ground your responses in this data — do not hallucinate
statistics or fabricate scenarios."""

def _format_match_context(match: dict, rounds: list[dict]) -> str:
    """Render one match's round-by-round data as a compact prompt section."""
    header = (
        f"\n## Match Under Review — {match.get('map', '?')} "
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

    if match_context and match_context.get("rounds"):
        player_context += _format_match_context(
            match_context.get("match", {}), match_context["rounds"]
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
