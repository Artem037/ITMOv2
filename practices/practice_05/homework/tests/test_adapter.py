"""HTTP contract: independent expectations, real HW4 calculation."""

import copy
import http.client
import json
import re
import subprocess
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

HOMEWORK = Path(__file__).resolve().parents[1]
ROOT = HOMEWORK.parents[2]
sys.path.insert(0, str(HOMEWORK))
FIXTURE = (
    ROOT
    / "practices/practice_04/homework/tests/fixtures/rare_connections.json"
)

try:
    from web.server import PlannerApplication, create_server
except ModuleNotFoundError as error:
    if error.name not in {"web", "web.server"}:
        raise
    PlannerApplication = create_server = None


@contextmanager
def running(payload):
    server = create_server(application=PlannerApplication(payload))
    thread = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.01), daemon=True
    )
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(
            create_server, "The local calculation adapter is not implemented"
        )
        self.original_bytes = FIXTURE.read_bytes()
        self.payload = json.loads(self.original_bytes)
        self.saved = copy.deepcopy(self.payload)
        self.context = running(self.payload)
        self.server = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)
        self.parameters = {
            key: copy.deepcopy(self.payload[key])
            for key in (
                "departure_window",
                "boarding_buffer_minutes",
                "max_options",
            )
        }

    def request(self, method, path, body=None, headers=None, server=None):
        connection = http.client.HTTPConnection(
            *(server or self.server).server_address, timeout=3
        )
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            data = response.read()
            self.assertIn(
                "application/json",
                response.getheader("Content-Type", ""),
                f"{method} {path} returned unstructured "
                f"HTTP {response.status}",
            )
            return (
                response.status,
                dict(response.getheaders()),
                json.loads(data),
            )
        finally:
            connection.close()

    def plan(self, parameters=..., server=None):
        return self.request(
            "POST",
            "/api/plan",
            json.dumps(self.parameters if parameters is ... else parameters),
            {"Content-Type": "application/json; charset=utf-8"},
            server,
        )

    def test_metadata_and_loopback(self):
        status, headers, result = self.request("GET", "/api/trip")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertEqual(result["defaults"], self.parameters)
        self.assertEqual(result["route"]["origin"], "Учебная точка А")
        self.assertEqual(result["schedule_dates"], ["2026-10-14"])
        self.assertEqual(result["data_kind"], "fixture")
        self.assertEqual(result["timezone"], "Europe/Moscow")

    def test_normal_response_preserves_entire_prior_core_result(self):
        status, _, result = self.plan()
        recorded = json.loads(
            (HOMEWORK / "evidence/contract-examples.json").read_text()
        )["cases"][0]["observed_core_result"]
        self.assertEqual(status, 200)
        self.assertEqual(result, recorded)

    def test_recalculation_uses_new_buffer(self):
        self.parameters["boarding_buffer_minutes"] = 20
        status, _, result = self.plan()
        self.assertEqual(status, 200)
        option = result["options"][0]
        self.assertEqual(option["leave_at"], "2026-10-14T09:25:00+03:00")
        self.assertEqual(option["arrive_at"], "2026-10-14T11:50:00+03:00")
        self.assertEqual(option["total_minutes"], 145)
        self.assertEqual(option["waiting_minutes"], 20)

    def test_no_routes_is_a_complete_calculation(self):
        self.parameters["departure_window"] = {
            "start": "2026-10-14T09:36:00+03:00",
            "end": "2026-10-14T10:00:00+03:00",
        }
        status, _, result = self.plan()
        self.assertEqual((status, result["status"]), (200, "no_routes"))
        self.assertTrue(result["search_scope"]["complete"])
        self.assertEqual(result["options"], [])
        self.assertTrue(result["warnings"] and result["sources"])

    def test_new_date_needs_data_without_moving_source(self):
        self.parameters["departure_window"] = {
            "start": "2026-10-15T06:00:00+03:00",
            "end": "2026-10-15T12:00:00+03:00",
        }
        status, _, result = self.plan()
        self.assertEqual((status, result["status"]), (200, "needs_data"))
        self.assertFalse(result["search_scope"]["complete"])
        self.assertEqual(result["sources"][0]["valid_dates"], ["2026-10-14"])

    def test_equal_boundary_includes_the_departure(self):
        self.parameters["departure_window"] = dict.fromkeys(
            ("start", "end"), "2026-10-14T09:35:00+03:00"
        )
        self.assertEqual(self.plan()[2]["options"][0]["total_minutes"], 135)

    def test_reverse_window_has_stable_field_and_recovers(self):
        original = copy.deepcopy(self.parameters)
        self.parameters["departure_window"]["end"] = (
            "2026-10-14T05:00:00+03:00"
        )
        status, _, result = self.plan()
        self.assertEqual(status, 422)
        self.assertEqual(result["error"]["field"], "departure_window.end")
        self.assertNotIn("status", result)
        self.assertEqual(self.plan(original)[2]["status"], "ok")

    def test_strict_numbers_and_ranges(self):
        for field, values in {
            "max_options": [None, True, "5", 5.0, 0, 6, 1.5],
            "boarding_buffer_minutes": [None, False, "10", 10.0, -1, 1441],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    parameters = copy.deepcopy(self.parameters)
                    parameters[field] = value
                    status, _, result = self.plan(parameters)
                    self.assertEqual(status, 422)
                    self.assertEqual(result["error"]["field"], field)
        for field, values in {
            "max_options": [1, 5],
            "boarding_buffer_minutes": [0, 1440],
        }.items():
            for value in values:
                with self.subTest(valid_field=field, value=value):
                    parameters = copy.deepcopy(self.parameters)
                    parameters[field] = value
                    self.assertEqual(self.plan(parameters)[0], 200)

    def test_moscow_datetime_grammar_and_calendar(self):
        for value in [
            "",
            None,
            123,
            "2026-02-30T06:00:00+03:00",
            "2026-10-14T06:00:00Z",
            "2026-10-14T06:00:00",
            "2026-10-14T06:00+03:00",
            "2026-10-14T06:00:00+02:00",
        ]:
            with self.subTest(value=value):
                parameters = copy.deepcopy(self.parameters)
                parameters["departure_window"]["start"] = value
                status, _, result = self.plan(parameters)
                self.assertEqual(status, 422)
                self.assertEqual(
                    result["error"]["field"], "departure_window.start"
                )

    def test_missing_extra_and_non_object_fields(self):
        missing = copy.deepcopy(self.parameters)
        del missing["max_options"]
        extra = {**self.parameters, "path": "/etc/passwd"}
        nested = copy.deepcopy(self.parameters)
        nested["departure_window"]["extra"] = 1
        for value in [missing, extra, nested, [], None, "text"]:
            with self.subTest(value=value):
                self.assertEqual(self.plan(value)[0], 422)

    def test_bad_json_duplicates_and_constants(self):
        for body in [b"{", b"\xff", b'{"a":1,"a":2}', b'{"a":NaN}']:
            with self.subTest(body=body):
                status, _, result = self.request(
                    "POST",
                    "/api/plan",
                    body,
                    {"Content-Type": "application/json"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(result["error"]["code"], "invalid_json")

    def test_media_type_and_fixed_routes(self):
        self.assertEqual(self.request("POST", "/api/plan", "{}")[0], 415)
        for path in ["/../../AGENTS.md", "/..%2fAGENTS.md", "/missing"]:
            self.assertEqual(self.request("GET", path)[0], 404)
        for method, path, allow in [
            ("GET", "/api/plan", "POST"),
            ("PUT", "/api/trip", "GET"),
            ("TRACE", "/api/trip", "GET"),
            ("CONNECT", "/api/plan", "POST"),
            ("BREW", "/api/trip", "GET"),
        ]:
            status, headers, result = self.request(method, path)
            self.assertEqual(status, 405)
            self.assertEqual(headers["Allow"], allow)
            self.assertEqual(result["error"]["code"], "method_not_allowed")

    def test_partial_success_is_not_replaced_by_needs_data(self):
        payload = copy.deepcopy(self.payload)
        payload["chains"][0]["coverage"] = "partial"
        with running(payload) as server:
            status, _, result = self.plan(server=server)
        self.assertEqual((status, result["status"]), (200, "ok"))
        self.assertFalse(result["search_scope"]["complete"])
        self.assertEqual(result["options"][0]["total_minutes"], 135)

    def test_fractional_durations_are_not_truncated(self):
        payload = copy.deepcopy(self.payload)
        payload["chains"][0]["stages"][0]["trips"][0]["arrival"] = (
            "2026-10-14T11:40:30+03:00"
        )
        with running(payload) as server:
            option = self.plan(server=server)[2]["options"][0]
        self.assertEqual(option["total_minutes"], 135.5)
        self.assertEqual(option["timeline"][2]["minutes"], 60.5)

    def test_unknown_duration_is_not_zero(self):
        payload = copy.deepcopy(self.payload)
        payload["chains"][0]["access"]["minutes"] = None
        with running(payload) as server:
            result = self.plan(server=server)[2]
        self.assertEqual(result["status"], "needs_data")
        self.assertEqual(result["options"], [])
        self.assertTrue(
            any("неизвестно" in text for text in result["warnings"])
        )

    def test_internal_error_is_safe_and_next_request_succeeds(self):
        with patch(
            "web.server.plan_departures", side_effect=RuntimeError("secret")
        ):
            status, _, result = self.plan()
        self.assertEqual(status, 500)
        self.assertEqual(result["error"]["code"], "internal_error")
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(self.plan()[2]["status"], "ok")

    def test_parallel_requests_and_repeats_do_not_mutate_snapshot(self):
        def calculate(buffer):
            parameters = {**self.parameters, "boarding_buffer_minutes": buffer}
            return self.plan(parameters)[2]["options"][0]["waiting_minutes"]

        with ThreadPoolExecutor(max_workers=4) as executor:
            observed = list(executor.map(calculate, [10, 20, 0, 15] * 2))
        self.assertEqual(observed, [10, 20, 0, 15] * 2)
        self.assertEqual(self.payload, self.saved)
        self.assertEqual(FIXTURE.read_bytes(), self.original_bytes)
        self.assertEqual(self.plan()[2]["options"][0]["total_minutes"], 135)

    def test_default_route_is_real_and_schedule_date_excludes_map_only_date(
        self,
    ):
        with running(None) as server:
            status, _, metadata = self.request(
                "GET", "/api/trip", server=server
            )
            self.assertEqual(status, 200)
            self.assertEqual(metadata["data_kind"], "real")
            self.assertEqual(metadata["schedule_dates"], ["2026-10-30"])
            self.assertEqual(
                metadata["route"]["origin"], "Метро «Проспект Славы»"
            )
            self.assertIn("9,2 км", metadata["route"]["description"])
            status, _, result = self.plan(metadata["defaults"], server=server)
        observed = json.loads(
            (HOMEWORK / "evidence/real-route-mcp.json").read_text()
        )["cases"][0]["result"]
        self.assertEqual(status, 200)
        self.assertEqual(result, observed)
        self.assertEqual(len(result["options"]), 3)
        self.assertEqual(result["options"][0]["total_minutes"], 253)

    def test_real_route_recalculation_negative_date_and_recovery(self):
        with running(None) as server:
            metadata = self.request("GET", "/api/trip", server=server)[2]
            self.assertEqual(metadata["data_kind"], "real")
            parameters = metadata["defaults"]
            before = copy.deepcopy(metadata)
            original = self.plan(parameters, server=server)[2]
            parameters["boarding_buffer_minutes"] = 20
            result = self.plan(parameters, server=server)[2]
            self.assertEqual(
                result["options"][0]["leave_at"], "2026-10-30T07:32:00+03:00"
            )
            self.assertEqual(result["options"][0]["total_minutes"], 263)
            parameters["boarding_buffer_minutes"] = 10
            for window, expected in [
                (
                    {
                        "start": "2026-10-30T08:00:00+03:00",
                        "end": "2026-10-30T08:10:00+03:00",
                    },
                    "no_routes",
                ),
                (
                    {
                        "start": "2026-10-31T06:00:00+03:00",
                        "end": "2026-10-31T10:00:00+03:00",
                    },
                    "needs_data",
                ),
            ]:
                parameters["departure_window"] = window
                result = self.plan(parameters, server=server)[2]
                self.assertEqual(result["status"], expected)
                self.assertEqual(
                    result["sources"][0]["valid_dates"], ["2026-10-30"]
                )
            after = self.request("GET", "/api/trip", server=server)[2]
            self.assertEqual(before, after)
            self.assertEqual(
                self.plan(after["defaults"], server=server)[2], original
            )

    def test_real_route_retains_late_trains_and_midnight_arrival(self):
        with running(None) as server:
            parameters = self.request("GET", "/api/trip", server=server)[2][
                "defaults"
            ]
            parameters["departure_window"] = {
                "start": "2026-10-30T22:40:00+03:00",
                "end": "2026-10-30T23:00:00+03:00",
            }
            result = self.plan(parameters, server=server)[2]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            result["options"][0]["arrive_at"], "2026-10-31T03:43:00+03:00"
        )
        rides = [
            event
            for event in result["options"][0]["timeline"]
            if event["kind"] == "ride"
        ]
        self.assertEqual(rides[0]["trip_id"], "6141")

    def test_fixed_fixture_launch_still_produces_control_metadata(self):
        process = subprocess.Popen(
            [
                sys.executable,
                str(HOMEWORK / "web/server.py"),
                "--fixture",
                "--port",
                "0",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            match = re.search(
                r"http://127\.0\.0\.1:[0-9]+", process.stdout.readline()
            )
            self.assertIsNotNone(
                match, "Fixed --fixture launch is unavailable"
            )
            with urlopen(match.group() + "/api/trip", timeout=3) as response:
                metadata = json.load(response)
            self.assertEqual(metadata["data_kind"], "fixture")
            self.assertEqual(metadata["schedule_dates"], ["2026-10-14"])
        finally:
            process.terminate()
            process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
