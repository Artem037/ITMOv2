"""Ручные ожидаемые значения: удаление запаса/валидации ломает тесты."""

import copy
import json
import unittest
from pathlib import Path

from trip_planner.models import InputError, parse_request
from trip_planner.planner import plan_departures

FIXTURE = Path(__file__).parent / "fixtures" / "rare_connections.json"


def request():
    return json.loads(FIXTURE.read_text())


def calculate(data):
    return plan_departures(parse_request(data))


class PlannerTests(unittest.TestCase):
    def test_departure_is_0935(self):
        result = calculate(request())
        self.assertEqual(result["status"], "ok")
        option = result["options"][0]
        self.assertEqual(option["leave_at"], "2026-10-14T09:35:00+03:00")
        self.assertEqual(option["arrive_at"], "2026-10-14T11:50:00+03:00")
        self.assertEqual(option["total_minutes"], 135)
        self.assertEqual(option["waiting_minutes"], 10)
        self.assertEqual(result["data_kind"], "fixture")

    def two_stages(self, arrival="10:25"):
        data = request()
        chain = data["chains"][0]
        chain["access"]["minutes"] = 20
        bus = chain["stages"][0]
        train = copy.deepcopy(bus)
        train["from_stop"] = "station-a"
        train["to_stop"] = "station-b"
        train["trips"][0].update(
            id="train-1",
            mode="suburban",
            label="Учебная электричка",
            departure="2026-10-14T09:00:00+03:00",
            arrival=f"2026-10-14T{arrival}:00+03:00",
        )
        chain["stages"] = [train, bus]
        chain["transfers"] = [
            {
                "from_stop": "station-b",
                "to_stop": "bus-a",
                "walk_minutes": 5,
                "buffer_minutes": 10,
            }
        ]
        return data

    def test_transfer_at_buffer_boundary(self):
        result = calculate(self.two_stages())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["options"][0]["waiting_minutes"], 20)
        self.assertEqual(result["options"][0]["transfer_count"], 1)
        timeline = result["options"][0]["timeline"]
        self.assertEqual(
            [x["kind"] for x in timeline],
            ["access", "wait", "ride", "walk", "wait", "ride", "egress"],
        )

    def test_missed_transfer_by_one_minute(self):
        self.assertEqual(
            calculate(self.two_stages("10:26"))["status"], "no_routes"
        )

    def test_overnight_is_30_minutes(self):
        data = request()
        data["departure_window"] = {
            "start": "2026-10-14T23:00:00+03:00",
            "end": "2026-10-15T00:00:00+03:00",
        }
        data["boarding_buffer_minutes"] = 0
        chain = data["chains"][0]
        chain["access"]["minutes"] = chain["egress"]["minutes"] = 0
        chain["stages"][0]["trips"][0].update(
            departure="2026-10-14T23:50:00+03:00",
            arrival="2026-10-15T00:20:00+03:00",
        )
        self.assertEqual(calculate(data)["options"][0]["total_minutes"], 30)

    def test_departure_window_includes_boundaries(self):
        for start, end, count in [
            ("09:35", "10:00", 1),
            ("09:00", "09:35", 1),
            ("09:36", "10:00", 0),
            ("09:00", "09:34", 0),
        ]:
            with self.subTest(start=start, end=end):
                data = request()
                data["departure_window"] = {
                    "start": f"2026-10-14T{start}:00+03:00",
                    "end": f"2026-10-14T{end}:00+03:00",
                }
                self.assertEqual(len(calculate(data)["options"]), count)

    def test_deduplicates_full_paths_without_padding(self):
        data = request()
        duplicate = copy.deepcopy(data["chains"][0])
        duplicate["id"] = "duplicate"
        data["chains"].append(duplicate)
        second = copy.deepcopy(duplicate["stages"][0]["trips"][0])
        second.update(
            id="bus-2",
            departure="2026-10-14T11:40:00+03:00",
            arrival="2026-10-14T12:30:00+03:00",
        )
        data["chains"][0]["stages"][0]["trips"].append(second)
        result = calculate(data)
        self.assertEqual(len(result["options"]), 2)
        self.assertEqual(result["options"][0]["total_minutes"], 125)
        self.assertEqual(
            result["options"][0]["leave_at"], "2026-10-14T10:35:00+03:00"
        )
        data["max_options"] = 1
        self.assertEqual(len(calculate(data)["options"]), 1)

    def test_unverified_and_wrong_date_are_not_confirmed(self):
        for change in [{"verified": False}, {"valid_dates": ["2026-10-13"]}]:
            data = request()
            data["sources"][0].update(change)
            result = calculate(data)
            self.assertEqual(result["status"], "needs_data")
            self.assertEqual(result["options"], [])
            self.assertTrue(result["warnings"])

    def test_partial_coverage_warns_even_if_option_exists(self):
        data = request()
        data["chains"][0]["coverage"] = "partial"
        result = calculate(data)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["warnings"])

    def test_no_routes_is_not_missing_data(self):
        data = request()
        data["chains"][0]["stages"][0]["trips"] = []
        self.assertEqual(calculate(data)["status"], "no_routes")
        data["chains"][0]["coverage"] = "missing"
        self.assertEqual(calculate(data)["status"], "needs_data")

    def test_rejects_invalid_requests(self):
        mutations = [
            lambda d: d.update(boarding_buffer_minutes=-1),
            lambda d: d.update(boarding_buffer_minutes=True),
            lambda d: d.update(max_options=0),
            lambda d: d.update(max_options=6),
            lambda d: d.update(timezone="UTC"),
            lambda d: d["departure_window"].update(
                end="2026-10-13T12:00:00+03:00"
            ),
            lambda d: d["departure_window"].update(
                start="2026-10-14T06:00:00"
            ),
            lambda d: d["chains"][0]["access"].update(minutes=-1),
            lambda d: d["chains"][0]["stages"][0]["trips"][0].update(
                source_id="absent"
            ),
            lambda d: d["chains"][0]["stages"][0]["trips"][0].update(
                arrival="2026-10-14T09:00:00+03:00"
            ),
            lambda d: d.update(unrecognized="typo"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                data = request()
                mutate(data)
                with self.assertRaises(InputError):
                    calculate(data)

    def test_transfer_must_connect_exact_stop_ids(self):
        data = self.two_stages()
        data["chains"][0]["transfers"][0]["to_stop"] = "same-name-other-stop"
        with self.assertRaises(InputError):
            calculate(data)
        data["chains"][0]["transfers"] = []
        with self.assertRaises(InputError):
            calculate(data)

    def test_sources_are_exposed_with_search_scope(self):
        result = calculate(request())
        self.assertEqual(result["sources"][0]["id"], "synthetic")
        self.assertIn("chains", result["search_scope"])


if __name__ == "__main__":
    unittest.main()
