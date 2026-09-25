import unittest

from framework.contracts import make_envelope, validate_envelope, CONTRACT_VERSION


class ContractsTest(unittest.TestCase):
    def test_valid_envelope(self):
        env = make_envelope(
            event_type="vehicle_task_submitted",
            event_id="vehicle_task_submitted:T1",
            timestamp="2026-01-01T00:00:00",
            payload={"task_id": "T1", "vehicle_id": "V001"},
        ).to_dict()
        self.assertIsNone(validate_envelope(env))

    def test_invalid_version(self):
        env = {
            "contract_version": "v0",
            "event_type": "task_completed",
            "event_id": "x",
            "timestamp": "t",
            "payload": {},
        }
        self.assertTrue(validate_envelope(env).startswith("version_mismatch"))


if __name__ == "__main__":
    unittest.main()
