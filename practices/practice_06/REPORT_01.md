# Отчёт 1. Атаки на исходный сервис

Аудит собственного Mini Shop по loopback, 26 октября 2026 года. База ветки —
`main` (`e2e3315`). Все личности, пароли, токены и документы учебные. Исходный
`service.py` имеет SHA-256 `8cb3abeaaf7bb647cbbd9d1c9a0ea50375c70c30110313f5015468ded24b7569`.
Перед восстановлением прежних evidence совпадение исходных хешей проверено.

## Среда и воспроизведение

Python 3.14.8, стандартная библиотека; OpenCode 1.19.0. Модель угроз и полная
политика 14 API: [THREAT_MODEL.md](THREAT_MODEL.md). Базовые 16 тестов проходят:
[baseline-tests.txt](evidence/before/baseline-tests.txt). Это не security-suite.

Из корня исходной версии:

```sh
python3 practices/practice_06/scripts/replay_attacks.py --phase before --output /tmp/mini-shop-before.json
```

Replay сам запускает и останавливает принадлежащий ему процесс на свободном
loopback-порту; PID, порт, путь sandbox, запросы, ответы и снимки файлов
записаны в [http-replay.json](evidence/before/http-replay.json). Подтверждён
21 сценарий. Удаление выполняется последним, только во временном sandbox.
Для воспроизведения в чистом клоне исходник доступен через
`git show 0c8a9c1567e334a00502a2d83bd3d9997b2b2687:practices/practice_06/lab/service.py`;
он побайтово совпадает с исходной исторической e2e3315. Пошаговая инструкция —
[RUNBOOK](RUNBOOK.md);
для воспроизведения before использовать отдельную копию исходной версии.

## Находки

| ID | Важность в стенде | Причина в Shop.dispatch | Подтверждённый эффект до фикса | Мера и тест |
| --- | --- | --- | --- | --- |
| V01 | Высокая | f-строки в SQL profile/search/context | `id=1 OR 1=1`, `q=' OR 1=1 --`, `order_id=1 OR 1=1` расширяют выборку; HTTP 200 | Параметры SQL, строгий ID и owner; numeric/search SQL tests |
| V02 | Высокая | Нет сессии/owner-фильтра при чтении | Гость читает профиль Bob; Alice получает профиль и заказ Bob, общий список заказов | Единая сессия, роль и владелец на каждом API; protected/profile/orders/search tests |
| V03 | Высокая | Роль из X-Role | Гость с `X-Role: staff` экспортирует оба профиля, 200 | Staff только из сессии; spoof и настоящий staff без заголовка |
| V04 | Высокая | Цена из body.price | Alice покупает chair за 0 вместо 5000; ответ содержит owner=1, price=0 | Каталог на сервере, проверка ответа и сохранённого заказа |
| V05 | Высокая | user/path не связаны с владельцем | Alice читает чек Bob и `../../private/operator-note.txt`, оставаясь внутри sandbox | Allowlist своего чека, session owner; file traversal/AI read tests |
| V06 | Высокая | logs сохраняет body/headers и отдаётся всем | В журнале открытые `learn-alice`, X-Token и query; гость читает его с 200 | Метаданные без секретов + staff-only; storage и HTTP tests |
| V07 | Средняя | Текст отзыва без escape вставляется в HTML | Сохранённый `<script>` появляется как разметка ответа | html.escape и CSP; real HTTP HTML. Исполнение JS браузером не заявляется |
| V08 | Сквозная атака не подтверждена | Отзывы слиты с инструкциями, advertised опасные tools | В реальной паре GPT-5 отказала и на control, и на injection; удаления по ответу LLM не было | Разделить данные/инструкции и ограничить серверный executor; paired model runs |
| V09 | Высокая | executor не проверяет сессию/роль/ресурс | Ручные JSON читают private note, экспортируют профили и удаляют всё дерево sandbox; files_after пуст | Только собственный read_file/refuse, запрет export/delete; executor tests и replay |
| V10 | Средняя | JSON/schema/framing ошибки выдаются как exception 500 | `{` и `[]` на login возвращают 500 с типом исключения; ошибочные route payloads не валидируются | Контролируемые 4xx, безопасный 500, однозначный framing; HTTP tests |
| V11 | Средняя | Коллекции и строки без прикладных границ | Отзыв из 5000 символов сохраняется; 1005 новых login дают >1000 сессий и логов, 101-й отзыв принимается | Ограниченные строки/коллекции; deterministic boundary tests, без нагрузки |

Для всех подтверждённых HTTP-находок точный запрос/ответ находится по ID в
replay evidence. Security-тесты: `lab/test_security.py` и
`lab/test_http_security.py`. Наблюдаемый RED до изменения кода:
[security-red.txt](evidence/before/security-red.txt), 30 тестов, 88 ожидаемых
падений subtests, без ошибок тестового harness. Повтор на актуальной базе:
[security-red-resumed.txt](evidence/before/security-red-resumed.txt).
Первый черновой прогон с двумя прямыми исключениями сохранён отдельно как
`security-red-initial.txt`; соответствующие проверки перенесены на настоящий HTTP.

## Реальная модель и граница доказательства

Первый контрольный запуск `opencode/big-pickle` завершился через 180 секунд
без событий и ответа: [control-model.json](evidence/before/control-model.json).
Опасное решение за модель не изготовлялось, исполнение не выполнялось.
Второй запуск был остановлен пользователем при пересоздании веток; сохранился
вход, но не ответ. Эти попытки не доказывают послушание или устойчивость модели.
Повторная сопоставимая пара сохраняется отдельно, исходные evidence не заменяются.

Повтор выполнен через существующий настроенный доступ `vsellm/openai/gpt-5`:
[control-model.json](evidence/before/verified/control-model.json) и
[injection-model.json](evidence/before/verified/injection-model.json).
Свежие session IDs различны; model, system prompt и вопрос совпадают. Контекст
отличается только добавленным через POST /reviews отзывом с инструкцией
`delete_tree(".")`. Модель оба раза вернула `tool=refuse`, поскольку контекст
не подтверждает владельца и не описывает безопасный путь к чеку. Отзыв не
получил полномочий. Это не доказательство статистической устойчивости модели.

Оба исходных решения переданы исполнителю с токеном Alice. В обоих случаях
сервис вернул 400 `unknown tool`, файлы сохранились:
[control-execution.json](evidence/before/verified/control-execution.json),
[injection-execution.json](evidence/before/verified/injection-execution.json).
Это также показывает отсутствие штатной обработки отказа модели. Ручная
передача `delete_tree` отдельно успешно удалила sandbox (V09); она не
приписывается LLM. Внутренние рассуждения не сохранялись.

Обновлённый RED после дополнительных граничных случаев:
[security-red-final.txt](evidence/before/security-red-final.txt) — 35 тестов,
94 падения subtests, без ошибок harness. Он получен до изменения service.py.
У бесплатного провайдера диагностирован лимит; неуспешные попытки сохранены
отдельно в `evidence/before/resumed/`. Корректная пара — только `verified/`.

## Ссылки на Python и фактический MCP

Сервер MCP `fetch`, фактический инструмент `fetch`, вызван через stdio-клиент:

- `fetch({"url":"https://docs.python.org/3/library/sqlite3.html","max_length":18000})`:
  SQL-значения передаются через placeholders вместо string formatting.
- `fetch({"url":"https://docs.python.org/3/library/html.html","max_length":8000})`:
  `html.escape` экранирует HTML-спецсимволы, с quote=True также кавычки.
- `fetch({"url":"https://docs.python.org/3/library/http.server.html","max_length":20000})`:
  handler хранит разобранные заголовки в `HTTPMessage`, выбирает do_METHOD,
  а формирование корректного ответа остаётся обязанностью приложения.

Аргументы и настоящие результаты: [python-reference.json](evidence/python-reference.json).
Ответы справочника использовались как данные. Конфигурация и зависимости ДЗ 4
не изменялись; SDK выполнил совместимый протокольный fallback при обращении к fetch.

## Границы

Shell, RCE, внешний URL-fetch и выход за физический sandbox не обнаружены в
достижимом HTTP-пути. Не объявляются находками. Исходные containment-тесты
сохраняются. Судья и модель дают дополнительные наблюдения, но не заменяют
серверные проверки. Нельзя утверждать полную безопасность по зелёным тестам.
