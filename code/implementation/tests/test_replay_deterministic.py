import unittest

from datasets import TrajectoryGenerator


class DeterministicReplayTest(unittest.TestCase):
    def test_trajectory_generator_is_deterministic(self):
        g1 = TrajectoryGenerator(num_vehicles=2, duration_s=10, sample_hz=2, seed=42)
        g2 = TrajectoryGenerator(num_vehicles=2, duration_s=10, sample_hz=2, seed=42)

        f1 = g1.generate_fleet()
        f2 = g2.generate_fleet()

        self.assertEqual(f1[0]["positions"][:5], f2[0]["positions"][:5])
        self.assertEqual(f1[1]["speeds"][:5], f2[1]["speeds"][:5])


if __name__ == "__main__":
    unittest.main()
