"""Реальный stdio-процесс: успех, ошибочный вход, восстановление."""

import json
import sys
import unittest
from pathlib import Path

from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_protocol_success_error_and_next_success(self):
        request = json.loads(
            (ROOT / "tests/fixtures/rare_connections.json").read_text()
        )
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "trip_planner.server"],
            cwd=ROOT,
        )
        async with Client(params, read_timeout_seconds=10) as client:
            listing = await client.list_tools()
            self.assertEqual(
                [tool.name for tool in listing.tools], ["plan_departures"]
            )
            success = await client.call_tool(
                "plan_departures", {"request": request}
            )
            self.assertFalse(success.is_error)
            result = success.structured_content
            self.assertEqual(result["status"], "ok")
            self.assertEqual(
                result["options"][0]["leave_at"], "2026-10-14T09:35:00+03:00"
            )
            request["boarding_buffer_minutes"] = -1
            failure = await client.call_tool(
                "plan_departures", {"request": request}
            )
            self.assertTrue(failure.is_error)
            message = " ".join(
                x.text for x in failure.content if hasattr(x, "text")
            )
            self.assertIn("boarding_buffer_minutes", message)
            request["boarding_buffer_minutes"] = 10
            recovered = await client.call_tool(
                "plan_departures", {"request": request}
            )
            self.assertFalse(recovered.is_error)
            self.assertEqual(recovered.structured_content["status"], "ok")


if __name__ == "__main__":
    unittest.main()
