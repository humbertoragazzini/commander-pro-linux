import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

CONFIG_DIR = Path.home() / ".config" / "commander-pro-control"
CONFIG_FILE = CONFIG_DIR / "config.json"

@dataclass
class AppSettings:
    fan_speeds: Dict[str, int]
    last_preset: str

    @classmethod
    def default(cls):
        return cls(
            fan_speeds={str(i): 50 for i in range(1, 7)},
            last_preset="BALANCED"
        )

def load_settings() -> AppSettings:
    if not CONFIG_FILE.exists():
        logger.info("Config file not found, creating default settings.")
        return AppSettings.default()
    
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return AppSettings(
                fan_speeds=data.get("fan_speeds", {str(i): 50 for i in range(1, 7)}),
                last_preset=data.get("last_preset", "BALANCED")
            )
    except Exception as e:
        logger.error(f"Failed to load config: {e}. Using defaults.")
        return AppSettings.default()

def save_settings(settings: AppSettings):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(settings), f, indent=4)
        logger.info(f"Settings saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
