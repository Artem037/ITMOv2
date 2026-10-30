"""Импорт данных, собранных skill из проверенных официальных источников."""

import json
from pathlib import Path

from trip_planner.models import InputError, PlanRequest, parse_request


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"Повторяющееся поле JSON: {key}")
        result[key] = value
    return result


def load_request(path: Path | str) -> PlanRequest:
    """Прочитать JSON, не меняя даты и степень подтверждения источников."""
    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError) as error:
        raise InputError(f"Не удалось прочитать {path}: {error}") from None
    except json.JSONDecodeError as error:
        raise InputError(
            f"Неверный JSON в {path}, строка {error.lineno}"
        ) from None
    return parse_request(payload)
