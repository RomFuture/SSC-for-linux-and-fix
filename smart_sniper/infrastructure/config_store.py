import json
import os
import sys
from pathlib import Path

from smart_sniper.application.ports import ConfigStorePort


def get_config_path() -> str:
    if sys.platform.startswith("linux"):
        config_dir = Path.home() / ".config" / "smart-sniper-czu"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "smart_sniper_config.json")

    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(application_path, "smart_sniper_config.json")


class JsonConfigStore(ConfigStorePort):
    def __init__(self, path: str | None = None) -> None:
        self.path = path or get_config_path()

    def load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as file:
                    return json.load(file)
            except Exception:
                return {}
        return {}

    def save(self, data: dict) -> None:
        try:
            existing = self.load()
            existing.update(data)
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(existing, file, ensure_ascii=False, indent=4)
        except Exception:
            pass

