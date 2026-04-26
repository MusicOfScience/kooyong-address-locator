import pandas as pd

from backend.analysis.live_count import current_margin, required_share_to_win, votes_counted_ratio


def test_margin_calculation():
    df = pd.DataFrame({"candidate": ["A", "B"], "votes": [5100, 4900]})
    assert round(current_margin(df), 2) == 2.0


def test_required_share_bounds():
    live = pd.DataFrame({"candidate": ["A", "B"], "votes": [5100, 4900]})
    dec = pd.DataFrame({"vote_type": ["postal"], "envelopes_remaining": [1000]})
    out = required_share_to_win(live, dec)
    assert 0 <= out <= 100


def test_votes_counted_ratio():
    live = pd.DataFrame({"candidate": ["A", "B"], "votes": [500, 500]})
    dec = pd.DataFrame({"vote_type": ["postal"], "envelopes_remaining": [1000]})
    assert votes_counted_ratio(live, dec) == 0.5
