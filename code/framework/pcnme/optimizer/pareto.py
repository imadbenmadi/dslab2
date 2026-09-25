from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class KneePoint:
    index: int
    point: np.ndarray


def select_knee_point(front: np.ndarray) -> KneePoint:
    """Select knee point on a 2D Pareto front using max distance-to-chord."""
    if front.ndim != 2 or front.shape[1] != 2:
        raise ValueError("front must be shape (n, 2)")
    if len(front) == 0:
        raise ValueError("front is empty")
    if len(front) <= 2:
        return KneePoint(index=0, point=front[0])

    # Normalize each objective to [0,1]
    mins = front.min(axis=0)
    spans = np.maximum(front.max(axis=0) - mins, 1e-9)
    norm = (front - mins) / spans

    order = np.argsort(norm[:, 0])
    points = norm[order]

    a = points[0]
    b = points[-1]
    ab = b - a
    ab_len = float(np.linalg.norm(ab))
    if ab_len < 1e-9:
        return KneePoint(index=int(order[0]), point=front[int(order[0])])

    # Distance from point p to line (a->b) in 2D:
    # |(b-a)x(a-p)| / |b-a|
    def dist_to_line(p: np.ndarray) -> float:
        ap = a - p
        cross = float(ab[0] * ap[1] - ab[1] * ap[0])
        return abs(cross) / ab_len

    distances = np.array([dist_to_line(p) for p in points], dtype=float)
    knee_sorted_idx = int(np.argmax(distances))
    knee_idx = int(order[knee_sorted_idx])
    return KneePoint(index=knee_idx, point=front[knee_idx])
