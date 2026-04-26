import numpy as np
import pandas as pd

from backend.models.forecast import aggregate_polls, monte_carlo_win_probability
from backend.models.preferences import tcp_from_preferences


def test_preference_flows_sum_to_one():
    a, b = tcp_from_preferences(0.42, 0.40, 0.18, 0.65)
    assert round(a + b, 8) == 1.0


def test_monte_carlo_sanity():
    result = monte_carlo_win_probability(1.0, n=1000, sigma=1.0)
    assert 0 <= result["win_probability"] <= 1
    assert result["ci_5"] < result["ci_95"]


def test_poll_aggregation():
    polls = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-08"],
            "party": ["A", "A"],
            "primary": [40, 42],
            "sample_size": [1000, 1600],
            "house_effect": [0, 0],
        }
    )
    out = aggregate_polls(polls)
    assert np.isfinite(out.loc[0, "weighted_primary"])
