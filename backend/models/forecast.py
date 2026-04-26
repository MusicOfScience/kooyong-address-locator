from __future__ import annotations

import numpy as np
import pandas as pd


def aggregate_polls(polls: pd.DataFrame, half_life_days: int = 14) -> pd.DataFrame:
    polls = polls.copy()
    max_date = pd.to_datetime(polls["date"]).max()
    age_days = (max_date - pd.to_datetime(polls["date"])).dt.days
    recency_weight = 0.5 ** (age_days / half_life_days)
    sample_weight = np.sqrt(polls["sample_size"].clip(lower=1))
    house_adj = polls.get("house_effect", 0)
    polls["combined_weight"] = recency_weight * sample_weight
    polls["adj_primary"] = polls["primary"] - house_adj
    out = (
        polls.groupby("party")
        .apply(lambda g: np.average(g["adj_primary"], weights=g["combined_weight"]))
        .reset_index(name="weighted_primary")
    )
    return out


def baseline_swing(historical: pd.DataFrame, latest_primary: pd.DataFrame) -> pd.DataFrame:
    merged = historical.groupby("party", as_index=False)["primary_prev"].mean().merge(
        latest_primary, on="party", how="left"
    )
    merged["weighted_primary"] = merged["weighted_primary"].fillna(merged["primary_prev"])
    merged["swing"] = merged["weighted_primary"] - merged["primary_prev"]
    return merged


def monte_carlo_win_probability(
    current_margin_pct: float,
    n: int = 4000,
    sigma: float = 1.8,
    seat_adjustment: float = 0.0,
    booth_adjustment: float = 0.0,
) -> dict:
    mean = current_margin_pct + seat_adjustment + booth_adjustment
    sims = np.random.normal(loc=mean, scale=sigma, size=n)
    p_lead = float((sims > 0).mean())
    return {
        "mean_margin": float(sims.mean()),
        "ci_5": float(np.percentile(sims, 5)),
        "ci_95": float(np.percentile(sims, 95)),
        "win_probability": p_lead,
        "distribution": sims,
    }
