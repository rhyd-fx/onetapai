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

You have access to the player's detailed analysis and relevant coaching
knowledge. Ground your responses in this data — do not hallucinate
statistics or fabricate scenarios."""

def build_coaching_prompt(
    player_profile: dict,
    retrieved_chunks: list[dict],
    user_question: str,
) -> list[dict]:
    """Assemble the full prompt with player context and retrieved knowledge."""

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

## ACS Variance (Feast-or-Famine Score)
- **CV Score**: {player_profile.get('acs_cv', 0):.3f} (>0.5 = feast-or-famine)
- **Score Range**: {player_profile.get('score_range', 'N/A')}

## Peek Analysis (Last 20 Matches)
- **Wide Swings**: {player_profile.get('wide_swing_pct', 0):.1f}%
- **Crossfire Deaths**: {player_profile.get('crossfire_death_pct', 0):.1f}%
- **Tight Peeks**: {player_profile.get('tight_peek_pct', 0):.1f}%

## Tilt Status
- **Session Tilt Probability**: {player_profile.get('tilt_probability', 0):.2f}
- **Session ACS Trend**: {player_profile.get('acs_slope', 'stable')}
"""

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
