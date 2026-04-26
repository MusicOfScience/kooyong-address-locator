from __future__ import annotations


def tcp_from_preferences(primary_a: float, primary_b: float, other: float, pref_to_a: float) -> tuple[float, float]:
    a = primary_a + other * pref_to_a
    b = primary_b + other * (1 - pref_to_a)
    total = a + b
    return (a / total, b / total) if total else (0.5, 0.5)
