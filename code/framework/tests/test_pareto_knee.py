import numpy as np

from pcnme.optimizer.pareto import select_knee_point


def test_select_knee_point_returns_valid_index():
    # A simple convex-like front
    front = np.array(
        [
            [1.0, 10.0],
            [2.0, 6.0],
            [3.0, 4.5],
            [4.0, 4.0],
            [5.0, 3.8],
        ],
        dtype=float,
    )
    knee = select_knee_point(front)
    assert 0 <= knee.index < len(front)
    assert knee.point.shape == (2,)
