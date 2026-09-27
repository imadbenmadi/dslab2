import unittest

from framework.messaging import CircuitBreaker, StoreForwardBuffer


class FaultInjectionTest(unittest.TestCase):
    def test_circuit_breaker_opens_and_recovers(self):
        cb = CircuitBreaker(fail_threshold=3, recovery_after=5)
        cb.on_failure(current_tick=10)
        cb.on_failure(current_tick=11)
        cb.on_failure(current_tick=12)

        self.assertTrue(cb.is_open(13))
        self.assertFalse(cb.is_open(18))

    def test_store_forward_buffer(self):
        buf = StoreForwardBuffer(capacity=3)
        buf.push({"id": 1})
        buf.push({"id": 2})
        buf.push({"id": 3})
        self.assertEqual(buf.size(), 3)
        items = buf.drain(limit=2)
        self.assertEqual(len(items), 2)
        self.assertEqual(buf.size(), 1)


if __name__ == "__main__":
    unittest.main()
