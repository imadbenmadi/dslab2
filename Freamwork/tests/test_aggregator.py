from pcnme.broker.aggregator import Aggregator
from pcnme.core.enums import TaskClass
from pcnme.core.task import DAGStep


def test_aggregator_does_not_aggregate_below_threshold():
    agg = Aggregator(q_max=10)
    steps = [DAGStep(id=1, name="a", MI=100, in_KB=10, out_KB=1)]
    decision = agg.maybe_aggregate(queue_depth=10, pending_steps=steps)
    assert decision.aggregated is False
    assert decision.task_class == TaskClass.PEBBLE


def test_aggregator_aggregates_above_threshold():
    agg = Aggregator(q_max=10)
    steps = [
        DAGStep(id=1, name="a", MI=100, in_KB=10, out_KB=1),
        DAGStep(id=2, name="b", MI=200, in_KB=5, out_KB=2),
    ]
    decision = agg.maybe_aggregate(queue_depth=11, pending_steps=steps)
    assert decision.aggregated is True
    assert decision.task_class == TaskClass.SUPER_PEBBLE
    assert decision.super_step is not None
    assert decision.super_step.MI == 300
    assert decision.super_step.in_KB == 15
    assert decision.super_step.out_KB == 3
