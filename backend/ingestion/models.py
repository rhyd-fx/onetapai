from pydantic import BaseModel, Field, field_validator
from enum import StrEnum
from typing import Optional


class DamageType(StrEnum):
    HEADSHOT = "headshot"
    BODYSHOT = "bodyshot"
    LEGSHOT = "legshot"
    UNKNOWN = "unknown"


# --- Henrik Dev API v3 Models ---
# These models validate the Henrik API response structure


class HenrikLocation(BaseModel):
    """X/Y coordinate from Henrik API."""
    x: float
    y: float


class HenrikPlayerLocation(BaseModel):
    """Player location snapshot at the moment of a kill."""
    player_puuid: str
    player_display_name: str
    player_team: str
    location: HenrikLocation
    view_radians: float


class HenrikAssistant(BaseModel):
    """Kill assistant info from Henrik API."""
    assistant_puuid: str
    assistant_display_name: str
    assistant_team: str


class HenrikKillEvent(BaseModel):
    """A kill event from Henrik's global kills array."""
    kill_time_in_round: int
    kill_time_in_match: int
    round: int = Field(ge=0, le=30)  # OT can push beyond 24
    killer_puuid: str
    killer_display_name: str
    killer_team: str
    victim_puuid: str
    victim_display_name: str
    victim_team: str
    victim_death_location: HenrikLocation
    damage_weapon_id: str = ""
    damage_weapon_name: str = "Unknown"
    secondary_fire_mode: bool = False
    player_locations_on_kill: list[HenrikPlayerLocation] = Field(default_factory=list)
    assistants: list[HenrikAssistant] = Field(default_factory=list)

    def get_killer_location(self) -> HenrikLocation | None:
        """Find the killer's location from the player_locations_on_kill array."""
        for loc in self.player_locations_on_kill:
            if loc.player_puuid == self.killer_puuid:
                return loc.location
        return None


class HenrikDamageEvent(BaseModel):
    """Per-victim damage breakdown within a round."""
    receiver_puuid: str
    receiver_display_name: str
    receiver_team: str
    bodyshots: int = 0
    headshots: int = 0
    legshots: int = 0
    damage: int = 0


class HenrikEconomy(BaseModel):
    """Per-round economy for a player."""
    loadout_value: int = 0
    remaining: int = 0
    spent: int = 0
    weapon: dict | None = None
    armor: dict | None = None


class HenrikRoundPlayerStats(BaseModel):
    """Per-round stats for a single player from Henrik's rounds[].player_stats[]."""
    player_puuid: str
    player_display_name: str
    player_team: str
    score: int = 0
    kills: int = 0
    damage: int = 0
    headshots: int = 0
    bodyshots: int = 0
    legshots: int = 0
    economy: HenrikEconomy = Field(default_factory=HenrikEconomy)
    was_afk: bool = False
    was_penalized: bool = False
    stayed_in_spawn: bool = False
    damage_events: list[HenrikDamageEvent] = Field(default_factory=list)
    kill_events: list[dict] = Field(default_factory=list)

    @field_validator("score")
    @classmethod
    def score_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Round score cannot be negative")
        return v


class HenrikPlantEvent(BaseModel):
    """Bomb plant event from Henrik API."""
    planted_by: dict | None = None
    plant_site: str | None = None
    plant_time_in_round: int | None = None
    plant_location: dict | None = None


class HenrikDefuseEvent(BaseModel):
    """Bomb defuse event from Henrik API."""
    defused_by: dict | None = None
    defuse_time_in_round: int | None = None
    defuse_location: dict | None = None


class HenrikRound(BaseModel):
    """A single round from Henrik API."""
    winning_team: str
    end_type: str
    bomb_planted: bool = False
    bomb_defused: bool = False
    plant_events: HenrikPlantEvent = Field(default_factory=HenrikPlantEvent)
    defuse_events: HenrikDefuseEvent = Field(default_factory=HenrikDefuseEvent)
    player_stats: list[HenrikRoundPlayerStats] = Field(default_factory=list)


# --- Internal normalized models (for DB insertion) ---


class KillEvent(BaseModel):
    """A normalized kill event ready for DB insertion."""
    killer_puuid: str
    victim_puuid: str
    round_num: int = Field(ge=0, le=30)
    time_in_round_ms: int = Field(ge=0)
    killer_x: float
    killer_y: float
    victim_x: float
    victim_y: float
    finishing_damage_type: DamageType = DamageType.UNKNOWN
    weapon: str
    assistants: list[str] = Field(default_factory=list)
    is_opening_kill: bool = False


class PlayerRoundStats(BaseModel):
    """Per-round stats for a single player, normalized for DB."""
    puuid: str
    round_num: int
    agent_id: str = "Unknown"
    team_id: str = "Unknown"
    score: int = 0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    damage_dealt: int = 0
    damage_received: int = 0
    headshots: int = 0
    bodyshots: int = 0
    legshots: int = 0
    economy_loadout_value: int = 0
    economy_remaining: int = 0
    economy_spent: int = 0
    was_afk: bool = False
    was_penalized: bool = False

    @field_validator("score")
    @classmethod
    def score_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Round score cannot be negative")
        return v


class PlayerLocation(BaseModel):
    """Snapshot of player position during a round."""
    puuid: str
    round_num: int
    view_radians: float
    x: float
    y: float
