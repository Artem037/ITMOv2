"""Security contract through real HTTP, including malformed transport input."""

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from service import Shop, make_handler


class HttpSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shop = Shop()
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(cls.shop)
        )
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()
        cls.shop.close()

    def raw(self, body, headers, method="POST", target="/login"):
        connection = http.client.HTTPConnection(
            *self.server.server_address, timeout=5
        )
        self.addCleanup(connection.close)
        connection.putrequest(method, target)
        for key, value in headers:
            connection.putheader(key, value)
        connection.endheaders(body)
        response = connection.getresponse()
        return (
            response.status,
            dict(response.getheaders()),
            response.read().decode(),
        )

    def request(self, body, auth=None, target="/login"):
        raw = json.dumps(body).encode()
        return self.raw(
            raw,
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(raw))),
                *(auth or {}).items(),
            ],
            target=target,
        )

    def login(self):
        status, _, text = self.request(
            {"username": "alice", "password": "learn-alice"}
        )
        self.assertEqual(status, 200)
        return {"X-Token": json.loads(text)["token"]}

    def test_bad_json_unicode_and_top_level_types_return_safe_400(self):
        for body in [b"{", b"\xff", b"[]", b"null", b"1", b'"abc"']:
            with self.subTest(body=body):
                status, _, result = self.raw(
                    body,
                    [
                        ("Content-Type", "application/json"),
                        ("Content-Length", str(len(body))),
                    ],
                )
                self.assertEqual(status, 400)
                self.assertNotIn("Error", result)
                self.assertNotIn("type", result)

    def test_invalid_content_length_is_400_and_oversize_is_413(self):
        for length, want in [("bad", 400), ("-1", 400), ("65537", 413)]:
            with self.subTest(length=length):
                self.assertEqual(
                    self.raw(
                        b"",
                        [
                            ("Content-Type", "application/json"),
                            ("Content-Length", length),
                        ],
                    )[0],
                    want,
                )

    def test_ambiguous_body_framing_is_rejected(self):
        for headers in [
            [("Content-Length", "2"), ("Content-Length", "3")],
            [("Content-Length", "2"), ("Transfer-Encoding", "chunked")],
            [],
        ]:
            with self.subTest(headers=headers):
                self.assertEqual(
                    self.raw(
                        b"{}", [("Content-Type", "application/json"), *headers]
                    )[0],
                    400,
                )

    def test_json_content_type_required_for_post(self):
        self.assertEqual(
            self.raw(
                b"{}",
                [("Content-Type", "text/plain"), ("Content-Length", "2")],
            )[0],
            415,
        )

    def test_invalid_route_payloads_do_not_throw_500(self):
        alice = self.login()
        for target, bodies in [
            ("/login", [{}, {"username": [], "password": {}}]),
            ("/orders", [{}, {"product": []}, {"product": 1}]),
            (
                "/reviews",
                [
                    {},
                    {"product": "chair", "text": 7},
                    {"product": "unknown", "text": "x"},
                ],
            ),
            (
                "/assistant/execute",
                [
                    {},
                    {"decision": None},
                    {"decision": []},
                    {"decision": {"tool": "read_file", "arguments": []}},
                    {"decision": {"tool": "read_file", "arguments": {}}},
                ],
            ),
        ]:
            for body in bodies:
                with self.subTest(target=target, body=body):
                    status, _, result = self.request(body, alice, target)
                    self.assertEqual(status, 400)
                    self.assertNotIn("Traceback", result)

    def test_header_names_are_case_insensitive(self):
        alice = self.login()
        status, _, result = self.raw(
            b"",
            [("x-token", alice["X-Token"])],
            method="GET",
            target="/profile?id=1",
        )
        self.assertEqual(status, 200)
        self.assertIn("TEST_ALICE", result)

    def test_structured_price_is_ignored_and_catalog_price_is_stored(self):
        status, _, text = self.request(
            {"product": "chair", "price": {"fake": 1}}, self.login(), "/orders"
        )
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(text)["price"], 5000)

    def test_absolute_file_argument_is_forbidden_without_internal_error(self):
        auth = self.login()
        status, _, body = self.raw(
            b"",
            list(auth.items()),
            method="GET",
            target="/files?user=alice&path=/etc/passwd",
        )
        self.assertEqual(status, 403)
        self.assertNotIn("FileNotFoundError", body)

    def test_review_response_has_browser_safety_headers(self):
        status, headers, _ = self.raw(
            b"", [], method="GET", target="/reviews/view"
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn(
            "default-src 'none'", headers.get("Content-Security-Policy", "")
        )

    def test_bad_request_does_not_break_following_good_request(self):
        self.raw(
            b"{",
            [("Content-Type", "application/json"), ("Content-Length", "1")],
        )
        self.assertEqual(
            self.raw(b"", [], method="GET", target="/health")[0], 200
        )

    def test_unexpected_internal_failure_does_not_expose_details(self):
        auth = self.login()
        with patch.object(
            self.shop.sandbox,
            "read",
            side_effect=RuntimeError("TEST_INTERNAL_SECRET"),
        ):
            status, _, body = self.raw(
                b"",
                list(auth.items()),
                method="GET",
                target="/files?user=alice&path=receipt.txt",
            )
        self.assertEqual(status, 500)
        self.assertNotIn("TEST_INTERNAL_SECRET", body)
        self.assertNotIn("RuntimeError", body)


if __name__ == "__main__":
    unittest.main()
