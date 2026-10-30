# Технический план реализации ДЗ5

27.10.2026, после принятия CONTRACT и обеих after; checkpoint 91994f0.
Штатный план: [Spec Kit plan](../../../specs/001-trip-planner-form/plan.md), список выполнения — [tasks](../../../specs/001-trip-planner-form/tasks.md).

| Владелец роли | Файлы / интерфейс | Проверка |
| --- | --- | --- |
| Логика (текущий implementer) | web/server.py: PlannerApplication(payload), metadata(), plan(parameters), create_server(port=0, application=None), main() | unittest через настоящий HTTP, fixture копии и неизменность |
| UI (текущий implementer) | web/index.html, style.css, app.js: mount формы, локальная revision/sequence, DOM безопасным textContent | Настоящий браузер, поздние ответы/ошибки и таймаут, keyboard/desktop/mobile |
| Координатор | Makefile, scripts/check.sh, .opencode/plugins/check-after-edit.js, tests/check-after-edit.test.mjs, документы | Новая step5, hook paths и исключение evidence, старая регрессия |

Порядок: тест адаптера RED → сервер GREEN → браузерные сценарии RED → экран GREEN → hook RED → пути GREEN → общая регрессия → converge/review → демо/отчёт. До production-кода всегда есть наблюдённый RED. Код ядра и lock не меняются.

Запуск: uv run --project practices/practice_04/homework --locked --offline python practices/practice_05/homework/web/server.py --port 8765. Импорт ядра привязан к расположению server.py. Сервер отдаёт лишь /, /app.js, /style.css, /api/trip и /api/plan. CLI --port — настройка локального запуска, не пользовательский путь HTTP.

Тесты используют unittest и node:test/Playwright. Установка нового web framework не нужна. Приёмку или общение исходных команд не выдумывать; after сведены текущим чатом и приняты человеком. Сравнение с OpenSpec основано на материалах отдельной classwork-ветки, без переключения текущей ветки.

## Расширение 29.10.2026

Поручение «добавь это» принято как согласованное расширение; спецификации/data
записаны3692527 до кода. T018–T023 продолжают ту же US3.
Обычный старт читает data/tolmachevo-2026-10-30.json, --fixture — фиксированный
старый fixture. Процесс использует только один снимок; HTTP не выбирает его.
Metadata route.description показывает оценки до расчёта, schedule_dates
считается по источникам расписанных этапов. UI меняет пометку по data_kind,
сохраняет все источники и показывает дату окончания ночного этапа.

Порядок подтверждён RED→GREEN:4 дополнительных HTTP теста,3 реальных browser
сценария и data-путь hook. Собственный stdio MCP отдельно проверил реальный
вход. Общие проверки, review и скриншоты — evidence/real-route-*.
Ядро, зависимости и прежняя fixture-регрессия сохранены.
