from __future__ import annotations

import numpy as np
import pandas as pd


def current_tcp(live_count: pd.DataFrame) -> pd.DataFrame:
    grouped = live_count.groupby("candidate", as_index=False)["votes"].sum()
    total = grouped["votes"].sum()
    grouped["share"] = grouped["votes"] / total if total else 0
    return grouped.sort_values("votes", ascending=False)


def current_margin(live_count: pd.DataFrame) -> float:
    table = current_tcp(live_count)
    if len(table) < 2:
        return 0.0
    return float((table.iloc[0]["share"] - table.iloc[1]["share"]) * 100)


def votes_counted_ratio(live_count: pd.DataFrame, declarations: pd.DataFrame) -> float:
    counted = float(live_count["votes"].sum())
    outstanding = float(declarations["envelopes_remaining"].sum())
    denom = counted + outstanding
    return counted / denom if denom else 0.0


def required_share_to_win(live_count: pd.DataFrame, declarations: pd.DataFrame) -> float:
    tcp = current_tcp(live_count)
    if len(tcp) < 2:
        return 50.0
    leader_votes, trailing_votes = float(tcp.iloc[0]["votes"]), float(tcp.iloc[1]["votes"])
    remaining = float(declarations["envelopes_remaining"].sum())
    deficit = leader_votes - trailing_votes
    req_votes = (remaining + deficit + 1) / 2
    return max(0.0, min(100.0, (req_votes / remaining) * 100 if remaining else 100.0))


def count_status(ratio: float, thresholds: dict) -> str:
    if ratio < thresholds["early"]:
        return "early"
    if ratio < thresholds["developing"]:
        return "developing"
    if ratio < thresholds["mature"]:
        return "mature"
    return "near-final"


def recount_risk_indicator(margin_pct: float) -> str:
    m = abs(margin_pct)
    if m < 0.3:
        return "High recount risk"
    if m < 0.8:
        return "Moderate recount risk"
    return "Low recount risk"


def sensitivity_by_vote_type(live_count: pd.DataFrame, declarations: pd.DataFrame) -> pd.DataFrame:
    margin = current_margin(live_count)
    rows = []
    for _, row in declarations.iterrows():
        leverage = np.clip((row["envelopes_remaining"] / declarations["envelopes_remaining"].sum()) * 100, 0, 100)
        rows.append({
            "vote_type": row["vote_type"],
            "envelopes_remaining": row["envelopes_remaining"],
            "sensitivity_score": round(leverage * (1 / max(abs(margin), 0.2)), 2),
        })
    return pd.DataFrame(rows).sort_values("sensitivity_score", ascending=False)
