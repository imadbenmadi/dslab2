from pcnme.broker.tof_broker import TOFBroker
from pcnme.core.enums import TaskClass


def test_tof_broker_classification_threshold_inclusive():
    broker = TOFBroker(fog_mips=2000, threshold_s=1.0)
    # EC = MI / fog_mips
    assert broker.classify(1999.0) == TaskClass.PEBBLE
    assert broker.classify(2000.0) == TaskClass.BOULDER
    assert broker.classify(2500.0) == TaskClass.BOULDER
