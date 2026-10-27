# Implementation Plan: форма повторного расчёта поездки

**Branch**: `practice_05` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)
**Input**: общая US3 и принятые CONTRACT/UI after/logic after; приёмка [AGREEMENT](../../practices/practice_05/homework/AGREEMENT.md), checkpoint `91994f0` до кода.

## Summary

Один экран и тонкий Python HTTP-адаптер вызывают существующие parse_request и plan_departures. HTML/CSS/JS не вычисляют маршрут. Исходный fixture неизменен, каждый вызов получает независимую копию. Реализация идёт в текущем чате; роли владения UI/logic определяют файлы, а не выдумывают второе обсуждение команд.

## Technical Context

**Language/Version**: Python 3.12+, browser ES modules, Node 24 для тестов.
**Primary Dependencies**: только стандартная библиотека адаптера и существующие locked Pydantic/MCP ядра; Playwright 1.62.1 — внешний инструмент браузерных тестов, не runtime приложения.
**Storage**: только чтение фиксированного fixture; нет записи состояния.
**Testing**: unittest + настоящий HTTP, Node node:test + Playwright + системный Chrome; Ruff из lock-файла ДЗ4.
**Target Platform**: локальный браузер, Python, loopback 127.0.0.1.
**Project Type**: один локальный экран и HTTP service.
**Performance Goals**: при fixture ответ приходит до клиентского предела 10 секунд; перебор ограничен существующим ядром.
**Constraints**: без UI-фреймворка, сети расписаний, shell из HTTP, произвольных путей, DB и изменения зависимостей ядра.
**Scale/Scope**: один пользователь, один снимок, одна US3, 4 значения формы.

## Constitution Check

| Принцип | До/после проектирования |
| --- | --- |
| I Одно ядро | PASS: импорт из ДЗ4; ни арифметика, ни схемы ядра не копируются |
| II Честные данные/МСК | PASS: +03:00, fixture, полный PlanResult, deepcopy, no_routes/needs_data/partial различены |
| III Приёмка до кода | PASS: точное принятие 27 октября записано и закоммичено 91994f0 |
| IV Проверяемые изменения | PASS design: обязательные RED/GREEN, HTTP/браузер и регрессия в задачах; результаты ещё предстоят |
| V Локальная история | PASS: loopback, фиксированная таблица ресурсов, нет shell/сети/записи |

Нет оправдываемых нарушений; повторная проверка после дизайна дала тот же результат.

## Project Structure

```text
specs/001-trip-planner-form/
  spec.md plan.md research.md data-model.md quickstart.md tasks.md
  contracts/http.md
practices/practice_05/homework/
  CONTRACT.md AGREEMENT.md IMPLEMENTATION_PLAN.md README.md REPORT.md
  specs/{ui,logic}.{before,after}.md
  web/__init__.py server.py index.html style.css app.js
  tests/test_adapter.py browser.test.mjs
  Makefile
  evidence/
```

**Structure Decision**: серверный модуль и статические файлы вместе в web, изолированные тесты в tests. Единственное ядро остаётся practices/practice_04/homework/trip_planner. Путь импорта вычисляется из __file__, не случайного cwd. Сервер имеет PlannerApplication(payload), metadata(), plan(parameters) и create_server(port=0, application=None); main читает --port, всегда bind 127.0.0.1. Внешний ввод никогда не выбирает payload.

## Phase 0: Research

[research.md](research.md) закрывает выбор сервера, JSON, московских дат, изоляции и доступного браузера. Нет NEEDS CLARIFICATION. Старый superpowers plugin отсутствует; текущий workflow выполняется через сохранённые repo skills Spec Kit, TDD и frontend-design, без установки нового плагина.

## Phase 1: Design

[data-model.md](data-model.md), [contracts/http.md](contracts/http.md), [quickstart.md](quickstart.md). Точный CONTRACT не дублируется: каноническая ссылка в contracts/. Метод/коды/состояния не меняются. Неизвестные поля и ошибочная структура — 422; плохой JSON — 400; базовая служебная проверка длины тела не запускает расчёт. Статика доступна лишь по явной таблице файлов.

## UI design review before code

Палитра: глубокий синий #153D67, фон #F6F9FC, голубой #DDEAF5, текст #1B2A39, вторичный #466579, учебный акцент #F5C76B. Шрифт Avenir Next/Trebuchet MS/Arial, числа tabular. Одна характерная деталь — полоса учебного маршрута и временная линия; это связь остановок и этапов, не карта. Нет маркетингового hero, градиентов и одинаковых карточек для всего.

Слева компактная форма, справа результат; на узком экране один поток. Выравнивание по левому краю, короткая длина строки. Warning виден, источники читаемы. Клавиатура/фокус/aria-live обязательны. После проверки плана убрана декоративная нумерация: номера остаются только у последовательности вариантов. Визуальный результат проверяется скриншотами desktop/mobile и исправляется по фактическому виду.

```text
[ Учебные данные ]  [ Дата расписания / МСК ]
Учебная точка А ───────── Учебная точка Б
[ окно / запас / лимит ] | [ выход → прибытие / длительности ]
[ Рассчитать          ] | [ этапы / предупреждения / источники ]
```

## Complexity Tracking

Нарушений constitution нет; DB/framework/дублирование ядра отклонены как лишняя сложность.
