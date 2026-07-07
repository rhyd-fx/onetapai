from dataclasses import dataclass

"""
Pipeline:
1. Identify high-quality coaching VOD reviews on YouTube
   (channels: EG Boostio, Woohoojin, JollzTV, etc.)
2. Extract transcripts via YouTube API / Whisper
3. Segment transcript by topic (agent, map, concept)
4. Clean and structure into chunked documents
5. Human review for accuracy
6. Embed and index into Qdrant
"""

@dataclass
class VODInsight:
    source_url: str
    coach_name: str
    timestamp_range: str            # "12:30–15:45"
    agent_discussed: str | None
    map_discussed: str | None
    concept_type: str               # positioning, utility, economy, mental
    rank_context: str               # "platinum player review"
    insight_text: str               # The actual coaching advice
    verified: bool = False          # Human-reviewed flag
