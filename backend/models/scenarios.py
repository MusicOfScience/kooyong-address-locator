from __future__ import annotations

import pandas as pd


def apply_scenario(live_count: pd.DataFrame, swing_a: float, turnout_mult: float) -> pd.DataFrame:
    df = live_count.copy()
    df["votes"] = df["votes"] * turnout_mult
    if len(df) >= 2:
        df.loc[df["candidate"] == df.iloc[0]["candidate"], "votes"] *= (1 + swing_a / 100)
        df.loc[df["candidate"] != df.iloc[0]["candidate"], "votes"] *= (1 - swing_a / 100)
    df["votes"] = df["votes"].clip(lower=0).round().astype(int)
    return df
