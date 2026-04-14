import numpy as np
import pytest

from pcnme.core.config import Settings
from pcnme.core.topology import CloudNode, FogNode, Position, Topology
from pcnme.optimizer.nsga2_mmde import MMDEMutation
from pcnme.optimizer.problem import OffloadingUnit, TaskOffloadingProblem


def _tiny_topology() -> Topology:
    fogs = [
        FogNode(id="FogA", name="A", pos=Position(x=0.0, y=0.0), mips=2000, initial_load=0.3),
        FogNode(id="FogB", name="B", pos=Position(x=100.0, y=0.0), mips=2000, initial_load=0.3),
    ]
    cloud = CloudNode(name="Cloud", mips=8000)
    return Topology(fog_nodes=fogs, cloud=cloud, fog_coverage_radius_m=50.0)


def test_problem_evaluate_shapes_and_penalty_out_of_coverage():
    settings = Settings()
    topo = _tiny_topology()
    units = [
        OffloadingUnit(unit_id="u1", mi=500.0, in_kb=10.0, out_kb=1.0, vehicle_xy=(0.0, 0.0), ingress_fog_id="FogA"),
        OffloadingUnit(unit_id="u2", mi=500.0, in_kb=10.0, out_kb=1.0, vehicle_xy=(0.0, 0.0), ingress_fog_id="FogA"),
    ]
    problem = TaskOffloadingProblem(settings=settings, topology=topo, units=units)

    # Two candidate solutions: all FogA vs all FogB
    X = np.array([[0, 0], [1, 1]], dtype=int)
    out = {}
    problem._evaluate(X, out)
    F = out["F"]
    assert F.shape == (2, 2)
    assert np.all(np.isfinite(F))

    # Now place vehicle far away so any fog assignment is infeasible, cloud remains feasible
    far_units = [OffloadingUnit(unit_id="u1", mi=500.0, in_kb=10.0, out_kb=1.0, vehicle_xy=(1e6, 1e6), ingress_fog_id=None)]
    far_problem = TaskOffloadingProblem(settings=settings, topology=topo, units=far_units)
    out2 = {}
    far_problem._evaluate(np.array([[0], [2]], dtype=int), out2)  # FogA vs CLOUD
    fog_cost = out2["F"][0]
    cloud_cost = out2["F"][1]
    assert fog_cost[0] >= 1e6
    assert cloud_cost[0] < 1e6


def test_mmde_mutation_respects_bounds_for_array_limits():
    settings = Settings()
    topo = _tiny_topology()
    units = [OffloadingUnit(unit_id="u1", mi=100.0, in_kb=10.0, out_kb=1.0, vehicle_xy=(0.0, 0.0), ingress_fog_id="FogA")]
    problem = TaskOffloadingProblem(settings=settings, topology=topo, units=units)

    np.random.seed(0)
    mutation = MMDEMutation(F=0.9, CR=1.0)
    X = np.array([[0], [1], [2], [0]], dtype=int)
    X2 = mutation._do(problem, X)
    assert X2.shape == X.shape
    assert np.all((X2 >= 0) & (X2 <= problem.xu.max()))
