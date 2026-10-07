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
    def test_same_departure_keeps_only_the_best_route(self):
        data = request()
        trips = data["chains"][0]["stages"][0]["trips"]
        slow = copy.deepcopy(trips[0])
        slow.update(id="slower-bus", arrival="2026-10-14T12:40:00+03:00")
        trips.insert(0, slow)
        options = calculate(data)["options"]
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["total_minutes"], 135)

    def test_unknown_access_is_missing_data_not_zero_minutes(self):
        data = request()
        data["chains"][0]["access"]["minutes"] = None
        result = calculate(data)
        self.assertEqual(result["status"], "needs_data")
        self.assertEqual(result["options"], [])

    def test_unverified_access_source_cannot_confirm_a_whole_trip(self):
        data = request()
        source = copy.deepcopy(data["sources"][0])
        source.update(id="map", verified=False)
        data["sources"].append(source)
        data["chains"][0]["access"]["source_ids"] = ["map"]
        self.assertEqual(calculate(data)["status"], "needs_data")

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
        data["chains"][0]["stages"][0]["source_ids"] = ["synthetic"]
        self.assertEqual(calculate(data)["status"], "no_routes")
        data["chains"][0]["coverage"] = "missing"
        self.assertEqual(calculate(data)["status"], "needs_data")

    def test_old_snapshot_cannot_rule_out_routes_on_another_date(self):
        data = json.loads(
            (
                FIXTURE.parents[2] / "examples/tolmachevo-2026-10-14.json"
            ).read_text()
        )
        data["departure_window"] = {
            "start": "2026-10-15T06:00:00+03:00",
            "end": "2026-10-15T10:00:00+03:00",
        }
        result = calculate(data)
        self.assertEqual(result["status"], "needs_data")
        self.assertFalse(result["search_scope"]["complete"])
        self.assertTrue(any("2026-10-15" in w for w in result["warnings"]))

    def test_empty_stage_needs_verified_dated_evidence(self):
        for refs, verified, dates in [
            ([], True, ["2026-10-14"]),
            (["synthetic"], False, ["2026-10-14"]),
            (["synthetic"], True, ["2026-10-13"]),
        ]:
            with self.subTest(refs=refs, verified=verified, dates=dates):
                data = request()
                stage = data["chains"][0]["stages"][0]
                stage.update(trips=[], source_ids=refs)
                data["sources"][0].update(verified=verified, valid_dates=dates)
                result = calculate(data)
                self.assertEqual(result["status"], "needs_data")
                self.assertFalse(result["search_scope"]["complete"])

    def test_coverage_uses_boarding_date_and_every_day_of_window(self):
        data = request()
        data["departure_window"] = {
            "start": "2026-10-13T23:00:00+03:00",
            "end": "2026-10-13T23:30:00+03:00",
        }
        self.assertEqual(calculate(data)["status"], "no_routes")
        data["departure_window"]["end"] = "2026-10-15T23:30:00+03:00"
        data["sources"][0]["valid_dates"] = ["2026-10-14", "2026-10-16"]
        self.assertFalse(calculate(data)["search_scope"]["complete"])

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

    def test_large_combination_input_is_rejected_before_calculation(self):
        data = self.two_stages()
        chain = data["chains"][0]
        third = copy.deepcopy(chain["stages"][1])
        third.update(from_stop="third-a", to_stop="third-b")
        chain["stages"].append(third)
        chain["transfers"].append(
            {
                "from_stop": "bus-b",
                "to_stop": "third-a",
                "walk_minutes": 5,
                "buffer_minutes": 5,
            }
        )
        for stage in chain["stages"]:
            stage["trips"] = [
                {**stage["trips"][0], "id": f"trip-{i}"} for i in range(100)
            ]
        with self.assertRaisesRegex(InputError, "50000.*сократите"):
            parse_request(data)
        # Небольшой запрос остаётся допустимым, без полного запрета 3 этапов.
        for stage in chain["stages"]:
            stage["trips"] = stage["trips"][:20]
        parse_request(data)

    def test_combination_budget_counts_all_chains_and_empty_tail(self):
        data = self.two_stages()
        chain = data["chains"][0]
        for stage in chain["stages"]:
            stage["trips"] *= 160
        other = copy.deepcopy(chain)
        other["id"] = "another"
        data["chains"].append(other)
        with self.assertRaisesRegex(InputError, "50000"):
            parse_request(data)
        # Пустой последний этап не отменяет перебор первых двух.
        data["chains"] = [chain]
        third = copy.deepcopy(chain["stages"][1])
        third.update(from_stop="third-a", to_stop="third-b", trips=[])
        chain["stages"].append(third)
        chain["transfers"].append(
            {
                "from_stop": "bus-b",
                "to_stop": "third-a",
                "walk_minutes": 0,
                "buffer_minutes": 0,
            }
        )
        for stage in chain["stages"][:2]:
            stage["trips"] *= 2
        with self.assertRaisesRegex(InputError, "50000"):
            parse_request(data)

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
