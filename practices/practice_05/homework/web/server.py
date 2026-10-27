"""Serve the fixed training route on loopback; calculate with HW4 only."""

import argparse
import copy
import json
import re
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CORE = ROOT / "practices/practice_04/homework"
FIXTURE = CORE / "tests/fixtures/rare_connections.json"
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
sys.path.insert(0, str(CORE))

from trip_planner.models import InputError, parse_request
from trip_planner.planner import plan_departures
from trip_planner.sources import load_request

MOMENT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+03:00"
)
LIMITS = {
    "boarding_buffer_minutes": {"min": 0, "max": 1440},
    "max_options": {"min": 1, "max": 5},
}


class AdapterError(ValueError):
    def __init__(self, status, code, message, field=None):
        super().__init__(message)
        self.status = status
        self.error = {"code": code, "message": message}
        if field:
            self.error["field"] = field


def invalid(message, field=None):
    raise AdapterError(422, "invalid_input", message, field)


def validate_parameters(parameters):
    if type(parameters) is not dict or set(parameters) != {
        "departure_window",
        "boarding_buffer_minutes",
        "max_options",
    }:
        invalid("Передайте окно выхода, запас на посадку и число вариантов.")
    window = parameters["departure_window"]
    if type(window) is not dict or set(window) != {"start", "end"}:
        invalid("Укажите начало и конец окна.", "departure_window")
    moments = []
    for key in ("start", "end"):
        value = window[key]
        try:
            if not isinstance(value, str) or not MOMENT.fullmatch(value):
                raise ValueError
            moments.append(datetime.fromisoformat(value))
        except ValueError:
            invalid(
                "Укажите корректные дату и время по Москве с +03:00.",
                f"departure_window.{key}",
            )
    for field, label in (
        ("boarding_buffer_minutes", "Запас на посадку"),
        ("max_options", "Число вариантов"),
    ):
        value = parameters[field]
        bounds = LIMITS[field]
        if (
            type(value) is not int
            or not bounds["min"] <= value <= bounds["max"]
        ):
            invalid(
                f"{label} должно быть целым числом "
                f"от {bounds['min']} до {bounds['max']}.",
                field,
            )
    if moments[1] < moments[0]:
        invalid(
            "Конец окна должен быть не раньше начала.", "departure_window.end"
        )


class PlannerApplication:
    def __init__(self, payload=None):
        request = (
            load_request(FIXTURE)
            if payload is None
            else parse_request(copy.deepcopy(payload))
        )
        self._snapshot = request.model_dump(mode="json")

    def metadata(self):
        snapshot = self._snapshot
        chain = snapshot["chains"][0]
        modes = {source["mode"] == "fixture" for source in snapshot["sources"]}
        return copy.deepcopy(
            {
                "route": {
                    key: chain[key] for key in ("id", "origin", "destination")
                },
                "timezone": snapshot["timezone"],
                "data_kind": "mixed"
                if len(modes) > 1
                else ("fixture" if True in modes else "real"),
                "schedule_dates": sorted(
                    {
                        day
                        for source in snapshot["sources"]
                        for day in source["valid_dates"]
                    }
                ),
                "sources": snapshot["sources"],
                "defaults": {
                    key: snapshot[key]
                    for key in (
                        "departure_window",
                        "boarding_buffer_minutes",
                        "max_options",
                    )
                },
                "limits": LIMITS,
            }
        )

    def plan(self, parameters):
        validate_parameters(parameters)
        payload = copy.deepcopy(self._snapshot)
        payload.update(copy.deepcopy(parameters))
        try:
            return plan_departures(parse_request(payload))
        except InputError as error:
            raise AdapterError(422, "invalid_input", str(error)) from None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Повтор поля JSON")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Недопустимая константа JSON")


def create_server(port=0, application=None):
    app = application if application is not None else PlannerApplication()

    class Handler(BaseHTTPRequestHandler):
        def __getattr__(self, name):
            if name.startswith("do_"):
                return self.dispatch
            raise AttributeError(name)

        def log_message(self, format, *args):
            pass

        def send_json(self, status, payload, allow=None):
            body = json.dumps(
                payload, ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if allow:
                self.send_header("Allow", allow)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def parameters(self):
            media_type = self.headers.get("Content-Type", "").split(";")[0]
            if media_type.strip().lower() != "application/json":
                raise AdapterError(
                    415, "unsupported_media_type", "Передайте JSON запроса."
                )
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError
                body = self.rfile.read(length).decode("utf-8")
                return json.loads(
                    body,
                    object_pairs_hook=unique_object,
                    parse_constant=reject_constant,
                )
            except (ValueError, UnicodeError):
                raise AdapterError(
                    400, "invalid_json", "Некорректный JSON запроса."
                ) from None

        def dispatch(self):
            allowed = {
                **dict.fromkeys(STATIC, "GET"),
                "/api/trip": "GET",
                "/api/plan": "POST",
            }
            if self.path not in allowed:
                self.send_json(
                    404,
                    {
                        "error": {
                            "code": "not_found",
                            "message": "Ресурс не найден.",
                        }
                    },
                )
                return
            method = allowed[self.path]
            if self.command != method:
                self.send_json(
                    405,
                    {
                        "error": {
                            "code": "method_not_allowed",
                            "message": "Метод недоступен.",
                        }
                    },
                    allow=method,
                )
                return
            try:
                if self.path in STATIC:
                    name, media_type = STATIC[self.path]
                    body = Path(__file__).with_name(name).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", media_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                result = (
                    app.metadata()
                    if self.path == "/api/trip"
                    else app.plan(self.parameters())
                )
                self.send_json(200, result)
            except AdapterError as error:
                self.send_json(error.status, {"error": error.error})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:  # noqa: BLE001 - Safe outer HTTP error boundary.
                self.send_json(
                    500,
                    {
                        "error": {
                            "code": "internal_error",
                            "message": (
                                "Не удалось выполнить расчёт. "
                                "Повторите запрос."
                            ),
                        }
                    },
                )

        do_GET = dispatch
        do_POST = dispatch
        do_PUT = dispatch
        do_PATCH = dispatch
        do_DELETE = dispatch
        do_OPTIONS = dispatch
        do_HEAD = dispatch

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        server = create_server(args.port)
    except (InputError, OSError):
        print("Не удалось запустить локальную форму.", file=sys.stderr)
        return 2
    print(f"Trip planner http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
