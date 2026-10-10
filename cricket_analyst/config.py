"""Central configuration."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("CRICKET_DB", DATA_DIR / "cricket.db"))
PLAYERS_CSV = Path(os.getenv("PLAYERS_CSV", DATA_DIR / "players.csv"))
KB_DIR = ROOT / "knowledge_base"
CHROMA_DIR = DATA_DIR / "chroma"

MODEL = os.getenv("CRICKET_MODEL", "openai/gpt-oss-120b")
MAX_BUILD_ITERS = int(os.getenv("MAX_BUILD_ITERS", "8"))
NEWS_MAX_AGE_HOURS = 24


@dataclass(frozen=True)
class FantasyRules:
    """Dream11-style defaults. Override per platform/league."""
    budget: float = 100.0
    size: int = 11
    max_per_team: int = 7
    roles: dict = field(default_factory=lambda: {
        "WK": (1, 4), "BAT": (3, 6), "AR": (1, 4), "BOWL": (3, 6)})
