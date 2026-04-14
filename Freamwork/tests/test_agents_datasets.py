import numpy as np

from pcnme.agents.agent1 import build_agent1_bc_dataset
from pcnme.agents.agent2 import build_agent2_bc_dataset, label_routing_action
from pcnme.core.config import Settings
from pcnme.core.topology import CloudNode, FogNode, Position, Topology


def _small_topology() -> Topology:
    fogs = [
        FogNode(id="FogA", name="A", pos=Position(x=0.0, y=0.0), mips=2000, initial_load=0.3),
        FogNode(id="FogB", name="B", pos=Position(x=200.0, y=0.0), mips=2000, initial_load=0.3),
    ]
    cloud = CloudNode(name="Cloud", mips=8000)
    return Topology(fog_nodes=fogs, cloud=cloud, fog_coverage_radius_m=250.0)


def test_agent1_bc_dataset_shapes_and_label_range():
    topo = _small_topology()
    settings = Settings(
        NSGA_POP_SIZE=10,
        NSGA_GENS=4,
        AGENT1_ACTION_DIM=len(topo.fog_ids()) + 1,
    )
    build = build_agent1_bc_dataset(settings=settings, topology=topo, batches=1, batch_size=8, seed=1)
    assert build.samples == 8
    assert build.dataset.X.shape == (8, settings.AGENT1_STATE_DIM)
    assert build.dataset.y.shape == (8,)
    assert int(build.dataset.y.min()) >= 0
    assert int(build.dataset.y.max()) < (len(topo.fog_ids()) + 1)


def test_agent2_bc_dataset_shapes_and_label_range():
    settings = Settings()
    build = build_agent2_bc_dataset(settings=settings, samples=64, seed=7)
    assert build.samples == 64
    assert build.dataset.X.shape == (64, settings.AGENT2_STATE_DIM)
    assert build.dataset.y.shape == (64,)
    assert int(build.dataset.y.min()) >= 0
    assert int(build.dataset.y.max()) < int(settings.AGENT2_ACTION_DIM)


def test_label_routing_action_returns_valid_action():
    settings = Settings()
    a = label_routing_action(
        settings=settings,
        queue_pressure=0.65,
        payload_kb=120.0,
        destination_is_cloud=True,
        preinstall_hit=False,
    )
    assert 0 <= int(a) < int(settings.AGENT2_ACTION_DIM)
