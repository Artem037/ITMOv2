"""Импорт должен сохранять происхождение и возвращать ошибки без traceback."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from trip_planner.models import InputError
from trip_planner.sources import load_request

FIXTURE = Path(__file__).parent / "fixtures" / "rare_connections.json"


class SourceTests(unittest.TestCase):
    def test_import_preserves_provenance_and_fixture_label(self):
        data = load_request(FIXTURE)
        self.assertEqual(data.sources[0].mode, "fixture")
        self.assertEqual(str(data.sources[0].valid_dates[0]), "2026-10-14")
        self.assertEqual(
            data.sources[0].checked_at.isoformat(), "2026-10-07T12:00:00+03:00"
        )

    def test_import_never_marks_unverified_source_verified(self):
        raw = json.loads(FIXTURE.read_text())
        raw["sources"][0]["verified"] = False
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            path.write_text(json.dumps(raw))
            self.assertFalse(load_request(path).sources[0].verified)

    def test_missing_and_broken_input_report_input_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            with self.assertRaisesRegex(InputError, "input.json"):
                load_request(path)
            path.write_text('{"sources":')
            with self.assertRaisesRegex(InputError, "JSON"):
                load_request(path)

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            path.write_text('{"max_options": 1, "max_options": 5}')
            with self.assertRaisesRegex(InputError, "max_options"):
                load_request(path)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "trip_planner.cli", *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_validate_cli_writes_normalized_request(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "normalized.json"
            result = self.run_cli(
                "validate", "--input", str(FIXTURE), "--output", str(output)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            normalized = json.loads(output.read_text())
            self.assertEqual(normalized["sources"][0]["mode"], "fixture")
            self.assertEqual(normalized["boarding_buffer_minutes"], 10)

    def test_plan_cli_uses_calculator_and_labels_fixture(self):
        result = self.run_cli("plan", "--input", str(FIXTURE))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(
            output["options"][0]["leave_at"], "2026-10-14T09:35:00+03:00"
        )
        self.assertEqual(output["data_kind"], "fixture")

    def test_cli_missing_file_is_actionable_without_traceback(self):
        result = self.run_cli("validate", "--input", "missing-input.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing-input.json", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
