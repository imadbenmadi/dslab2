from __future__ import annotations


def clip(value: float, lo: float, hi: float) -> float:
    return float(min(max(float(value), float(lo)), float(hi)))


def normalise(value: float, denom: float, cap: float) -> float:
    if denom == 0:
        return 0.0
    return float(min(float(value) / float(denom), float(cap)))
