GROUNDING_SUFFIX = """

IMPORTANT CONSTRAINTS:
1. Every stat you cite MUST come from the Player Profile above.
   Do NOT invent or round statistics.
2. Every strategic recommendation MUST be supported by at least
   one retrieved knowledge source. Cite it as [Source N].
3. If you lack sufficient data to answer, say so explicitly
   and suggest what additional data would help.
4. Drill recommendations MUST account for the player's eDPI.
   Do NOT recommend generic drills without hardware calibration.
5. Structure your response with clear sections:
   - What you're doing well
   - Key areas for improvement (prioritized)
   - Specific action items (with drill names/durations)
   - Mental/strategic note (if relevant)

FORMATTING:
- Reply in clean GitHub-flavored Markdown.
- Use `## ` (with a trailing space) for section headers, `**bold**` for key
  terms, and `-` bullet lists for action items. Keep it concise and skimmable.
- Only use a Markdown table when comparing 2+ items across the same columns,
  and keep tables small (<= 3 columns). Otherwise prefer bullets.
"""
