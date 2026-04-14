import math

from pcnme.mobility.predictor import compute_t_exit


def test_compute_t_exit_outside_returns_zero_and_false():
    res = compute_t_exit(vehicle_pos=(100.0, 0.0), vehicle_speed_ms=10.0, vehicle_heading_deg=0.0, fog_pos=(0.0, 0.0), fog_radius_m=50.0)
    assert res.in_coverage is False
    assert res.t_exit_s == 0.0


def test_compute_t_exit_inside_heading_outward_gives_finite():
    # Start at x=25 inside radius 50, move +x (heading 0)
    res = compute_t_exit(vehicle_pos=(25.0, 0.0), vehicle_speed_ms=5.0, vehicle_heading_deg=0.0, fog_pos=(0.0, 0.0), fog_radius_m=50.0)
    assert res.in_coverage is True
    assert math.isfinite(res.t_exit_s)
    # Remaining distance to boundary is 25m; speed 5m/s -> 5s
    assert abs(res.t_exit_s - 5.0) < 1e-6


def test_compute_t_exit_inside_heading_inward_infinite():
    # Start at x=25, move towards origin (-x): should not exit (infinite)
    res = compute_t_exit(vehicle_pos=(25.0, 0.0), vehicle_speed_ms=5.0, vehicle_heading_deg=180.0, fog_pos=(0.0, 0.0), fog_radius_m=50.0)
    assert res.in_coverage is True
    assert res.t_exit_s == float("inf")
