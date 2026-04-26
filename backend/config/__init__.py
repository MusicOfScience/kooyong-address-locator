from pathlib import Path
import yaml


def load_contest_config(path: str | None = None) -> dict:
    cfg_path = Path(path) if path else Path(__file__).with_name("contest_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
