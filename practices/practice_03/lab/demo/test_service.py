import unittest

import service
from service import subscribe, subscribers


class SubscribeTest(unittest.TestCase):
    def setUp(self):
        subscribers.clear()

    def test_subscribe(self):
        self.assertEqual(subscribe("Ann"), {"subscribed": True})
        self.assertEqual(subscribers, {"Ann"})

    def test_empty(self):
        with self.assertRaises(ValueError):
            subscribe(" ")

    def test_duplicate(self):
        subscribe("Ann")
        subscribe("Ann")
        self.assertEqual(len(subscribers), 1)

    def test_unsubscribe_removes_existing(self):
        subscribe("Ann")
        self.assertTrue(callable(getattr(service, "unsubscribe", None)))
        self.assertEqual(service.unsubscribe(" Ann "), {"unsubscribed": True})
        self.assertEqual(subscribers, set())

    def test_unsubscribe_missing_is_safe(self):
        try:
            result = service.unsubscribe("Ann")
        except KeyError:
            self.fail("missing subscriber must not raise KeyError")
        self.assertEqual(result, {"unsubscribed": False})
        self.assertEqual(subscribers, set())

    def test_unsubscribe_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            service.unsubscribe("  ")
        self.assertEqual(subscribers, set())


if __name__ == "__main__":
    unittest.main()
