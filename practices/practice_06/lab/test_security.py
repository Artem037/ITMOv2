"""Regression tests for demonstrated trust-boundary failures; no LLM needed."""

import json
import unittest
from urllib.parse import urlencode

from service import Shop


class SecurityTest(unittest.TestCase):
    def setUp(self):
        self.shop = Shop()
        self.addCleanup(self.shop.close)
        self.alice = self.login("alice")
        self.bob = self.login("bob")
        self.staff = self.login("staff")

    def call(self, method, path, body=None, auth=None):
        with self.shop.lock:
            return self.shop.dispatch(
                method, path, {} if body is None else body, auth or {}
            )

    def login(self, name):
        status, data = self.call(
            "POST", "/login", {"username": name, "password": "learn-" + name}
        )
        self.assertEqual(status, 200)
        return {"X-Token": data["token"]}

    def test_protected_routes_require_real_session(self):
        for auth in [{}, {"X-Token": "not-a-session"}, {"X-Role": "staff"}]:
            for method, path, body in [
                ("GET", "/profile?id=1", None),
                ("GET", "/search?q=TEST", None),
                ("GET", "/orders", None),
                ("GET", "/files", None),
                ("GET", "/admin/export", None),
                ("GET", "/debug/logs", None),
                ("GET", "/assistant/context", None),
                ("POST", "/orders", {"product": "chair"}),
                ("POST", "/reviews", {"product": "chair", "text": "review"}),
                (
                    "POST",
                    "/assistant/execute",
                    {"decision": {"tool": "export_profiles"}},
                ),
            ]:
                with self.subTest(auth=auth, path=path):
                    self.assertEqual(
                        self.call(method, path, body, auth)[0], 401
                    )

    def test_profile_and_context_reject_other_owner(self):
        for auth, other in [(self.alice, 2), (self.bob, 1)]:
            for target in [
                f"/profile?id={other}",
                f"/assistant/context?order_id={other}",
            ]:
                with self.subTest(target=target):
                    status, body = self.call("GET", target, auth=auth)
                    self.assertEqual(status, 403)
                    self.assertNotIn("TEST_ADDRESS", json.dumps(body))
                    self.assertNotIn(
                        "lamp" if other == 2 else "chair", json.dumps(body)
                    )

    def test_orders_are_scoped_to_customer(self):
        for auth, owner in [(self.alice, 1), (self.bob, 2)]:
            status, orders = self.call("GET", "/orders", auth=auth)
            self.assertEqual(status, 200)
            self.assertEqual([order["owner"] for order in orders], [owner])

    def test_search_wildcard_does_not_bypass_owner(self):
        status, rows = self.call(
            "GET", "/search?" + urlencode({"q": "%"}), auth=self.alice
        )
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in rows], [1])

    def test_numeric_sql_injections_are_rejected(self):
        for path, key in [
            ("/profile", "id"),
            ("/assistant/context", "order_id"),
        ]:
            with self.subTest(path=path):
                self.assertEqual(
                    self.call(
                        "GET",
                        path + "?" + urlencode({key: "1 OR 1=1"}),
                        auth=self.alice,
                    )[0],
                    400,
                )

    def test_search_sql_injection_is_literal_data(self):
        self.assertEqual(
            self.call(
                "GET",
                "/search?" + urlencode({"q": "' OR 1=1 --"}),
                auth=self.alice,
            ),
            (200, []),
        )

    def test_staff_export_uses_session_without_role_header(self):
        status, rows = self.call("GET", "/admin/export", auth=self.staff)
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in rows], [1, 2])

    def test_customer_cannot_spoof_staff(self):
        for target in ["/admin/export", "/debug/logs"]:
            self.assertEqual(
                self.call(
                    "GET", target, auth={**self.alice, "X-Role": "staff"}
                )[0],
                403,
            )

    def test_price_is_from_catalog_in_response_and_database(self):
        for price in [0, -100, "free", None]:
            with self.subTest(price=price):
                status, order = self.call(
                    "POST",
                    "/orders",
                    {"product": "chair", "price": price},
                    self.alice,
                )
                self.assertEqual(status, 201)
                self.assertEqual(order["price"], 5000)
        stored = self.call("GET", "/orders", auth=self.alice)[1]
        self.assertTrue(all(order["price"] == 5000 for order in stored))

    def test_files_reject_other_customer_and_private_traversal(self):
        for user, path in [
            ("bob", "receipt.txt"),
            ("alice", "../bob/receipt.txt"),
            ("alice", "../../private/operator-note.txt"),
        ]:
            with self.subTest(user=user, path=path):
                status, body = self.call(
                    "GET",
                    "/files?" + urlencode({"user": user, "path": path}),
                    auth=self.alice,
                )
                self.assertEqual(status, 403)
                self.assertNotIn("TEST_BOB", json.dumps(body))
                self.assertNotIn("TEST_ONLY_OPERATOR_SECRET", json.dumps(body))

    def test_executor_rechecks_file_owner_and_forbids_export_and_delete(self):
        for tool, arguments in [
            ("read_file", {"path": "files/bob/receipt.txt"}),
            ("read_file", {"path": "private/operator-note.txt"}),
            ("export_profiles", {}),
            ("delete_tree", {"path": "."}),
        ]:
            with self.subTest(tool=tool, arguments=arguments):
                status, body = self.call(
                    "POST",
                    "/assistant/execute",
                    {"decision": {"tool": tool, "arguments": arguments}},
                    self.alice,
                )
                self.assertEqual(status, 403)
                self.assertNotIn("TEST_BOB", json.dumps(body))
                self.assertTrue(
                    (
                        self.shop.sandbox.root / "files/alice/receipt.txt"
                    ).exists()
                )
                self.assertTrue(
                    (self.shop.sandbox.root / "files/bob/receipt.txt").exists()
                )

    def test_executor_allows_model_refusal_without_side_effect(self):
        status, data = self.call(
            "POST",
            "/assistant/execute",
            {
                "decision": {
                    "tool": "refuse",
                    "arguments": {"reason": "no legal action"},
                }
            },
            self.alice,
        )
        self.assertEqual(status, 200)
        self.assertIn("refused", data)
        self.assertTrue(
            (self.shop.sandbox.root / "files/alice/receipt.txt").exists()
        )

    def test_staff_cannot_use_customer_executor(self):
        self.assertEqual(
            self.call(
                "POST",
                "/assistant/execute",
                {
                    "decision": {
                        "tool": "delete_tree",
                        "arguments": {"path": "."},
                    }
                },
                self.staff,
            )[0],
            403,
        )
        self.assertTrue(self.shop.sandbox.root.exists())

    def test_logs_do_not_store_password_token_body_or_query(self):
        self.call(
            "GET",
            "/search?" + urlencode({"q": "PRIVATE_QUERY"}),
            auth=self.alice,
        )
        text = json.dumps(self.shop.logs)
        for secret in [
            "learn-alice",
            self.alice["X-Token"],
            "PRIVATE_QUERY",
            "learn-bob",
        ]:
            with self.subTest(secret=secret):
                self.assertNotIn(secret, text)

    def test_customer_cannot_read_debug_logs(self):
        self.assertEqual(
            self.call("GET", "/debug/logs", auth=self.alice)[0], 403
        )

    def test_reviews_render_untrusted_markup_as_text(self):
        text = '<script>alert("TEST")</script><img src=x onerror=alert(1)>'
        self.assertEqual(
            self.call(
                "POST",
                "/reviews",
                {"product": "chair", "text": text},
                self.alice,
            )[0],
            201,
        )
        html = self.call("GET", "/reviews/view")[1]
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img ", html)
        self.assertIn("&lt;script&gt;", html)

    def test_long_review_is_rejected_without_storage(self):
        self.assertEqual(
            self.call(
                "POST",
                "/reviews",
                {"product": "chair", "text": "x" * 5000},
                self.alice,
            )[0],
            400,
        )
        self.assertEqual(self.shop.reviews, [])

    def test_review_collection_has_a_limit(self):
        for _ in range(100):
            self.assertEqual(
                self.call(
                    "POST",
                    "/reviews",
                    {"product": "chair", "text": "ok"},
                    self.alice,
                )[0],
                201,
            )
        self.assertEqual(
            self.call(
                "POST",
                "/reviews",
                {"product": "chair", "text": "overflow"},
                self.alice,
            )[0],
            429,
        )

    def test_session_and_log_memory_are_bounded(self):
        for _ in range(1005):
            self.login("alice")
        self.assertLessEqual(len(self.shop.sessions), 1000)
        self.assertLessEqual(len(self.shop.logs), 1000)
        self.assertEqual(
            self.call("GET", "/profile?id=1", auth=self.alice)[0], 401
        )

    def test_new_order_does_not_return_old_purchase_receipt(self):
        status, order = self.call(
            "POST", "/orders", {"product": "lamp"}, self.alice
        )
        self.assertEqual(status, 201)
        status, context = self.call(
            "GET",
            f"/assistant/context?order_id={order['id']}",
            auth=self.alice,
        )
        self.assertEqual(status, 200)
        self.assertIn("refuse", context["prompt"])
        self.assertNotIn("files/alice/receipt.txt", context["prompt"])

    def test_purchase_collection_has_a_limit_without_extra_insert(self):
        for _ in range(998):
            self.assertEqual(
                self.call("POST", "/orders", {"product": "lamp"}, self.alice)[
                    0
                ],
                201,
            )
        self.assertEqual(
            self.call("POST", "/orders", {"product": "lamp"}, self.alice)[0],
            429,
        )
        self.assertEqual(len(self.shop.rows("SELECT * FROM orders")), 1000)

    def test_oversized_numeric_id_is_a_client_error(self):
        for path in ["/profile?id=", "/assistant/context?order_id="]:
            self.assertEqual(
                self.call("GET", path + "9" * 100, auth=self.alice)[0], 400
            )

    def test_duplicate_query_parameter_is_not_silently_selected(self):
        self.assertEqual(
            self.call("GET", "/profile?id=1&id=2", auth=self.alice)[0], 400
        )

    def test_executor_rejects_malformed_arguments_and_extra_capabilities(self):
        for decision in [
            {
                "tool": "read_file",
                "arguments": {
                    "path": "files/alice/receipt.txt",
                    "role": "staff",
                },
            },
            {"tool": "unknown", "arguments": {}},
        ]:
            status, _ = self.call(
                "POST",
                "/assistant/execute",
                {"decision": decision},
                self.alice,
            )
            self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
