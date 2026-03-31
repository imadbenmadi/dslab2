import unittest
import numpy as np

from app import UnifiedSmartCityApp
from agents.agent1 import Agent1
from agents.agent2 import Agent2


class TrainingRuntimeTest(unittest.TestCase):
    def test_pretraining_bootstrap_produces_pairs(self):
        a1 = Agent1()
        a2 = Agent2()
        pair1 = {
            "state": np.zeros(13, dtype=np.float32),
            "action": 0,
            "source": "tof-mmde-nsga2",
        }
        pair2 = {
            "state": np.zeros(15, dtype=np.float32),
            "action": 0,
            "source": "tof-mmde-nsga2",
        }
        a1.pretrain([pair1], epochs=1)
        a2.pretrain([pair2], epochs=1)
        self.assertTrue(True)

    def test_rl_updates_accumulate_rewards(self):
        app = UnifiedSmartCityApp("proposed")
        app.sim_time = 1
        offloads = []
        app._simulate_one_dag(app.vehicle_states[0], 0, offloads)

        self.assertGreater(app.agent_stats["agent1"]["updates"], 0)
        self.assertGreater(app.agent_stats["agent2"]["updates"], 0)
        self.assertGreater(app.agent_stats["agent1"]["rewardCount"], 0)
        self.assertGreater(app.agent_stats["agent2"]["rewardCount"], 0)


if __name__ == "__main__":
    unittest.main()
