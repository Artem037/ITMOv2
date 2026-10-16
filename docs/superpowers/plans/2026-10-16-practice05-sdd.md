# Практика 5 Фильтр подписчиков Notify Mini Implementation Plan

> Выполнение: OpenSpec `filter-notify-mini-subscribers`, схема `spec-driven`. Чекбоксы отражают фактический прогресс; архивирование выполняется после пользовательской приёмки.

**Goal:** Добавить небольшую персональную фичу — фильтр существующего списка подписчиков по части имени — и пройти исследование, требования, RED/GREEN, локальный запуск и проверку.

**Architecture:** Расширить `list_subscribers(query="")`, сохранив старый вызов. Очистить запрос через `strip().casefold()`, отобрать исходные имена по подстроке и применить прежний `sorted`. Новых модулей, хранилищ или интерфейсов не требуется.

**Tech Stack:** Python 3.10+, стандартная библиотека, unittest, Ruff, Make; OpenSpec 1.14.1, профиль core, Codex/OpenCode.

**Spec:** Текущая база — `openspec/specs/notify-mini/spec.md`; пять условий новой фичи — `openspec/changes/filter-notify-mini-subscribers/specs/notify-mini/spec.md`. Proposal, design и tasks находятся рядом.

## Уточнённое задание

Пользователь подтвердил, что преподаватель разрешил свой проект, затем по слайдам уточнил необходимость одной маленькой фичи. Выбран Notify Mini и фильтр существующего списка. Подготовительный рефакторинг уже выполнен, но не заменяет эту фичу; его история и доказательства описаны в `practices/practice_05/lab/REFACTOR.md`.

## Global Constraints

- Работать из `/Users/pip/ITMOv2`, ветка `practice-05`; без push.
- Соблюдать `AGENTS.md` и STYLE_GUIDE демо; только стандартная библиотека и память процесса.
- Старые результаты, отчёты, настройки практики 3 и домашку 4 сохранять.
- Домашняя работа 5 и третья User Story не входят в объём занятия.
- Для нового поведения: тесты → ожидаемый RED → минимальный код → GREEN.
- Официальные контракты Python получать через настоящий MCP fetch, сохранять URL, аргументы и результат.
- Перед действием объяснять цель по-русски, после — доказательство и результат.
- Итог: `sh scripts/check.sh`, затем `git diff --check`, `openspec validate --all --strict`.

## Review Focus

1. Подстрока в середине имени, разный регистр, Unicode casefold (`Straße`/`STRASSE`).
2. Пустая строка и пробельный запрос возвращают полный отсортированный список.
3. Отсутствие совпадений и пустое состояние возвращают `[]`.
4. Старые вызовы без аргументов, подписка и отписка сохраняют поведение.
5. Фильтр не меняет состояние, написание имён, сортировку и независимость списка.

## Файлы

| Путь | Роль |
| --- | --- |
| `practices/practice_03/lab/demo/service.py` | Необязательный query и фильтрация |
| `practices/practice_03/lab/demo/test_service.py` | Пять новых тестов; всего 17 |
| `practices/practice_03/lab/demo/README.md` | Пример фильтра и запуска из корня |
| `openspec/changes/filter-notify-mini-subscribers/` | Proposal, delta spec, design, tasks |
| `practices/practice_05/lab/REPORT.md` | Объяснение процесса и инструкция показа |
| `practices/practice_05/lab/evidence/filter-*.txt` | Реальные baseline, MCP, RED, GREEN, demo, checks |
| `practices/practice_05/lab/evidence/filter-review.md` | Независимое ревью новой фичи |

## Порядок выполнения

- [x] **1. Explore и baseline:** прочитать код, тесты, README и OpenSpec context, выделить пять условий; выполнить 12 исходных тестов. Доказательство: `filter-baseline.txt`.
- [x] **2. Сформировать change:** `openspec new change filter-notify-mini-subscribers`, получить инструкции для артефактов, оформить proposal/spec/design/tasks и проверить strict validation. Подтвердить `str.casefold` через MCP: `filter-python-docs-mcp.txt`.
- [x] **3. RED:** добавить `test_list_filters_substring_without_case`, `test_list_filter_trims_query`, `test_list_filter_blank_query_returns_all`, `test_list_filter_without_matches_returns_empty`, `test_list_filter_preserves_state`; запустить тесты до реализации. Ожидаемо отсутствующий query дал 6 TypeError в пяти новых тестах, включая два subtest; прежние 12 прошли. Доказательство: `filter-red.txt`.
- [x] **4. GREEN:** реализовать `list_subscribers(query="")`, сохранить старые контракты, дополнить README. Пройти все 17 тестов и общий runner. Доказательство: `filter-green.txt`, код `573dc6c`.
- [x] **5. Локальный показ:** выполнить из корня `python3 -i practices/practice_03/lab/demo/service.py`; показать запрос с пробелами/регистром, пустой запрос, отсутствие совпадений и неизменный полный список. Сохранить `filter-demo.txt` и команду в REPORT.
- [x] **6. Независимое ревью:** проверить пять фокусов, соответствие delta коду, тесты и отчёт; записать `filter-review.md`, устранить существенные замечания с проверками.
- [x] **7. Завершение:** пройти `sh scripts/check.sh` (17 + 28 + 6 = 51 тест), `git diff --check`, `openspec validate --all --strict`; сохранить `filter-checks.txt`, обновить tasks и этот план, сделать локальные коммиты.

## После пользовательской приёмки

- [ ] Синхронизировать принятую delta в основную spec и архивировать change штатным OpenSpec workflow.

Локальный показ выполняется существующим Python-модулем в одном процессе. Новый HTTP-сервер не добавляется. Факт запуска и проверки не подменяет решение преподавателя об оценке.
