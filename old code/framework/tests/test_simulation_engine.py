import asyncio

from pcnme.core.config import Settings
from pcnme.core.topology import CloudNode, FogNode, Position, Topology
from pcnme.simulation.engine import SimulationEngine


class DummyStore:
    def __init__(self):
        self.states = []
        self.metrics = []

    async def set_latest_state(self, state):
        self.states.append(state)

    async def append_metric(self, metric):
        self.metrics.append(metric)


def test_engine_runs_and_publishes_state():
    settings = Settings(SIM_DURATION_S=1.0, N_VEHICLES=2, TASK_RATE_HZ=0.0, Q_MAX=10)
    topo = Topology(
        fog_nodes=[
            FogNode(id="FogA", name="A", pos=Position(x=0.0, y=0.0), mips=2000, initial_load=0.3),
        ],
        cloud=CloudNode(name="Cloud", mips=8000),
        fog_coverage_radius_m=250.0,
    )
    store = DummyStore()
    engine = SimulationEngine(settings=settings, topology=topo, store=store)  # type: ignore[arg-type]

    async def run():
        await engine.start()
        await engine.stop()

    asyncio.run(run())
    assert len(store.states) >= 1
    latest = store.states[-1]
    assert "vehicles" in latest
    assert "fogs" in latest
    assert "metrics" in latest
