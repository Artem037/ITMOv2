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

    def test_subscribe_trims_name(self):
        self.assertEqual(subscribe(" Ann "), {"subscribed": True})
        self.assertEqual(subscribers, {"Ann"})
        self.assertIs(service.subscribers, subscribers)

    def test_empty_names_preserve_existing_subscribers(self):
        subscribe("Ann")
        for operation in (subscribe, service.unsubscribe):
            for name in ("", " \t\n"):
                with self.subTest(operation=operation.__name__, name=name):
                    with self.assertRaisesRegex(ValueError, "^empty name$"):
                        operation(name)
                    self.assertEqual(subscribers, {"Ann"})

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

    def test_repeated_unsubscribe_returns_false(self):
        subscribe("Ann")
        self.assertEqual(service.unsubscribe("Ann"), {"unsubscribed": True})
        self.assertEqual(service.unsubscribe("Ann"), {"unsubscribed": False})
        self.assertEqual(subscribers, set())

    def test_list_subscribers_sorted_without_mutation(self):
        subscribe("Zoe")
        subscribe("Ann")
        original_subscribers = subscribers.copy()
        self.assertTrue(callable(getattr(service, "list_subscribers", None)))
        self.assertEqual(service.list_subscribers(), ["Ann", "Zoe"])
        self.assertEqual(subscribers, original_subscribers)

    def test_list_subscribers_empty(self):
        self.assertTrue(callable(getattr(service, "list_subscribers", None)))
        self.assertEqual(service.list_subscribers(), [])

    def test_list_result_is_detached(self):
        subscribe("Ann")
        names = service.list_subscribers()
        names.append("Zoe")
        self.assertEqual(subscribers, {"Ann"})
        self.assertEqual(service.list_subscribers(), ["Ann"])

    def test_list_filters_substring_without_case(self):
        for name in ("Bob", "Joanna", "Ann", "Straße"):
            subscribe(name)
        self.assertEqual(service.list_subscribers("AN"), ["Ann", "Joanna"])
        self.assertEqual(service.list_subscribers("STRASSE"), ["Straße"])

    def test_list_filter_trims_query(self):
        for name in ("Bob", "Anna", "Ann"):
            subscribe(name)
        self.assertEqual(service.list_subscribers(" \tAN\n "), ["Ann", "Anna"])

    def test_list_filter_blank_query_returns_all(self):
        subscribe("Zoe")
        subscribe("Ann")
        for query in ("", " \t\n"):
            with self.subTest(query=query):
                self.assertEqual(
                    service.list_subscribers(query), ["Ann", "Zoe"]
                )

    def test_list_filter_without_matches_returns_empty(self):
        self.assertEqual(service.list_subscribers("zz"), [])
        subscribe("Bob")
        self.assertEqual(service.list_subscribers("zz"), [])

    def test_list_filter_preserves_state(self):
        for name in ("Bob", "Ann", "Anna"):
            subscribe(name)
        names = service.list_subscribers("ann")
        names.append("Zoe")
        self.assertEqual(subscribers, {"Ann", "Anna", "Bob"})
        self.assertEqual(service.list_subscribers("ann"), ["Ann", "Anna"])
        self.assertEqual(service.list_subscribers(), ["Ann", "Anna", "Bob"])


if __name__ == "__main__":
    unittest.main()
