"""Проверка входного файла и воспроизводимый запуск расчёта без агента."""

import argparse
import json
import sys
from pathlib import Path

from trip_planner.models import InputError
from trip_planner.planner import plan_departures
from trip_planner.sources import load_request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "plan"])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        request = load_request(args.input)
        result = (
            request.model_dump(mode="json")
            if args.command == "validate"
            else plan_departures(request)
        )
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except (InputError, OSError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
