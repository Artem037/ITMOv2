# Tasks: форма повторного расчёта поездки

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/http.md; принятые CONTRACT и обе after.
**Tests**: обязательны по constitution IV и TDD. Одна история US3 (P1), US1/US2 — существующая база.

## Phase 1: Setup

- [x] T001 Записать принятие до кода в practices/practice_05/homework/AGREEMENT.md и evidence/human-acceptance.json, checkpoint 91994f0.
- [x] T002 Выполнить planning workflow и заполнить specs/001-trip-planner-form/plan.md, research.md, data-model.md, contracts/http.md, quickstart.md и practices/practice_05/homework/IMPLEMENTATION_PLAN.md.

## Phase 2: Foundational

- [x] T003 Проверить spec/plan/tasks через speckit-analyze; сохранить результат в practices/practice_05/homework/evidence/analysis.md и gates из checklists/requirements.md (FR-013).

## Phase 3: US3 — пересчёт подготовленного маршрута (P1)

**Goal**: форма вызывает одно ядро и объясняет исход, ошибку и повтор.
**Independent test**: настоящий браузер → исходный успех → запас20 → no_routes → needs_data → ошибка → исправление → успех. Снимок неизменен.

- [ ] T004 [US3] Добавить реальные HTTP/ядро проверки в practices/practice_05/homework/tests/test_adapter.py: метаданные, расчёт, границы, ошибки, полное/частичное покрытие, дроби и отсутствие мутации; наблюдать RED (FR-001–003, 006–008, 010–012).
- [ ] T005 [US3] Реализовать PlannerApplication и loopback/fixed routes в practices/practice_05/homework/web/server.py с __init__.py; parse_request/plan_departures, JSON и ошибки C-01–05; получить GREEN без изменения ядра (FR-001–003, 006–008, 010–012).
- [ ] T006 [US3] Добавить tests/browser.test.mjs: настоящий экран/расчёт, ошибки/исправление, зоны, статусы, источники и доступность; наблюдать RED отсутствующего экрана (FR-001–009).
- [ ] T007 [US3] Реализовать web/index.html, style.css, app.js: один экран, формы, metadata, POST, полный результат/пометки/источники, local revision/sequence и таймаут; получить GREEN (FR-001–010, 012).
- [ ] T008 [US3] Доказать управляемыми ответами в tests/browser.test.mjs оба порядка A/B, позднюю ошибку, двойную отправку, 10 секунд, partial ok, дроби и непригодный ответ; основной E2E оставить с настоящим ядром (FR-007–009).
- [ ] T009 [US3] Выполнить desktop/mobile и keyboard проверки через tests/browser.test.mjs, сохранить screenshots в evidence/ и исправить видимые проблемы web/style.css (FR-001, 004–005, 008–009).

## Phase 4: Polish and integration

- [ ] T010 Проверить новые пути web/tests/Makefile hook через RED в tests/check-after-edit.test.mjs, затем расширить .opencode/plugins/check-after-edit.js, сохранив исключение evidence и старые проверки (FR-011).
- [ ] T011 Добавить practices/practice_05/homework/Makefile, step5 в Makefile и новую часть в scripts/check.sh с Ruff, unittest, браузером; сохранить старые цели (FR-011–012).
- [ ] T012 Пройти sh scripts/check.sh, make test, git diff --check; сохранить точные команды/выводы/exit codes в practices/practice_05/homework/evidence/final-checks.txt (FR-011).
- [ ] T013 Выполнить speckit-converge по spec/plan/tasks и принятым ролевым документам; сохранить practices/practice_05/homework/evidence/convergence.md; закрыть реальные пробелы, если найдены (FR-013).
- [ ] T014 Выполнить независимый итоговый review кода и контрактных границ; сохранить practices/practice_05/homework/evidence/review.md, исправить существенные замечания и повторить затронутые проверки.
- [ ] T015 Записать воспроизводимое демо успеха/ошибки/границы в practices/practice_05/homework/evidence/demo.md, приложить фактические браузерные screenshots (FR-001–012).
- [ ] T016 Подготовить practices/practice_05/homework/README.md и REPORT.md: запуск, проверки, границы, сравнение реальных Spec Kit/OpenSpec, рефлексия и сдача.
- [ ] T017 Обновить docs/superpowers/plans/2026-10-20-practice05-homework.md и practices/practice_05/homework/FRAMEWORK.md фактическими стадиями; сохранить локальные коммиты, отдельную публикацию не выполнять.

## Dependencies and execution order

T001 → T002 → T003 → T004 RED → T005 GREEN → T006 RED → T007 GREEN → T008 → T009 → T010 RED/GREEN → T011 → T012 → T013 → T014 → T015–T017. При новых исправлениях после review повторить затронутые тесты и final checks.

**Parallel opportunities**: исследование Python/browser в Phase 0 независимо от документации; после готовой реализации T014 read-only review может идти параллельно с T015/T016. Не поручать двум авторам один файл. В текущем run один implementer, независимый reviewer только читает код.

**MVP**: одна US3 целиком; статусы/ошибки/неизменность входят в MVP. Не вводить отдельные новые истории, произвольные маршруты и публикацию.
