# Tasks

## 1. Контракт и baseline

- [x] 1.1 Прочитать текущий список и тесты, зафиксировать пять условий фильтра в delta spec; выполнить 12 исходных тестов и сохранить `evidence/filter-baseline.txt`, проверить `openspec validate filter-notify-mini-subscribers --strict`.
- [x] 1.2 Проверить Unicode caseless matching в официальной Python-документации через MCP fetch; сохранить реальный вызов и ответ в `evidence/filter-python-docs-mcp.txt`.

## 2. RED и GREEN

- [x] 2.1 Добавить пять тестов фильтра: подстрока/регистр/Unicode, пробелы, пустой запрос, отсутствие совпадений и пустой сервис, неизменность состояния; наблюдать ожидаемый RED на отсутствии query и сохранить `evidence/filter-red.txt`.
- [x] 2.2 Реализовать `list_subscribers(query="")` минимальным изменением, выполнить все 17 тестов демо и сохранить GREEN в `evidence/filter-green.txt`; дополнить README примером и совместимым вызовом без аргументов.

## 3. Локальный показ и приёмка

- [x] 3.1 Из корня запустить существующий Python-модуль, показать пять условий фильтра; сохранить реальный PTY в `evidence/filter-demo.txt` и инструкции в `lab/REPORT.md`.
- [x] 3.2 Независимо проверить code/spec/tests/report, устранить существенные замечания; сохранить итог в `evidence/filter-review.md`.
- [x] 3.3 Выполнить `sh scripts/check.sh`, `git diff --check` и `openspec validate --all --strict`; сохранить `evidence/filter-checks.txt`, обновить план и локальные коммиты в practice-05 без push.

## Workflow follow-up

- После пользовательской приёмки синхронизировать delta и архивировать change штатным OpenSpec workflow.
