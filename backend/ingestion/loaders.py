from __future__ import annotations

from pathlib import Path
import pandas as pd


def load_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported format: {path.suffix}")


def load_sample_bundle(base_dir: str | Path = "data/sample") -> dict[str, pd.DataFrame]:
    base = Path(base_dir)
    return {
        "booths": load_table(base / "booths.csv"),
        "live_count": load_table(base / "live_count.csv"),
        "declarations": load_table(base / "declaration_votes.csv"),
        "historical": load_table(base / "historical_booth_results.csv"),
        "polls": load_table(base / "polls.csv"),
        "commentary": load_table(base / "commentary.csv"),
        "intelligence": load_table(base / "intelligence.csv"),
        "candidates": load_table(base / "candidates.csv"),
    }
