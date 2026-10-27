# Phase 0: решения и источники

27.10.2026. Read-only исследование отдельного исследовательского агента по speckit-plan; код/файлы агент не менял.

| Решение | Причина | Альтернатива |
| --- | --- | --- |
| ThreadingHTTPServer + BaseHTTPRequestHandler, 127.0.0.1 | Независимые вызовы, фиксированные ресурсы, без новых runtime dependencies | SimpleHTTPRequestHandler даёт ненужную файловую маршрутизацию; web framework лишний |
| object_pairs_hook и parse_constant; allow_nan=False | Python JSON по умолчанию принимает дубли/NaN; договор запрещает | Обычный loads теряет информацию о повторе |
| type(value) is int | bool — подкласс int; нужны строгие целые | isinstance(value, int) ошибочно пропускает bool |
| deepcopy полного снимка | Поверхностная копия разделяет вложенные данные | Смена окна в общем dict нарушит неизменность |
| regex HTTP-грамматики + datetime.fromisoformat | Сам parser принимает более широкий ISO, чем договор; затем нужна календарная проверка | Наивный Date в JS зависит от зоны компьютера |
| Node node:test + Playwright 1.62.1 + системный Chrome | Уже доступны; без установки/изменения core lock | @playwright/test отсутствует; bundled Chromium 1234 отсутствует |

Официальные Python 3.12 источники: [http.server](https://docs.python.org/3.12/library/http.server.html), [json](https://docs.python.org/3.12/library/json.html), [copy](https://docs.python.org/3.12/library/copy.html), [datetime](https://docs.python.org/3.12/library/datetime.html#datetime.datetime.fromisoformat), [bool](https://docs.python.org/3.12/library/stdtypes.html#boolean-type-bool).

По AGENTS требовался fetch MCP. Универсальный fetch в текущем ALL_TOOLS отсутствует; GitHub fetch не читает Python Docs. Фактически применён tools.web__run: open четырёх URL http.server/json/copy/datetime с response_length=long; затем open stdtypes#boolean-type-bool и уточняющие open json/http.server/datetime; find по stdtypes (bool is a subclass of int) и datetime (datetime.fromisoformat). Это fallback, не заявляется выполненный fetch-вызов. Страницы использованы только как справочные данные.

Фактическая проверка окружения: Node v24.19.0; playwright 1.62.1 в bundled node_modules. Первая попытка launch bundled Chromium завершилась missing executable; запуск системного Chrome /Applications/Google Chrome.app/Contents/MacOS/Google Chrome дал exit 0, версию 156.0.8078.48 и timezone America/New_York. Зависимости не скачивались. Для переносимости тест принимает PLAYWRIGHT_MODULE_PATH и BROWSER_EXECUTABLE, затем ищет локальный playwright/bundled runtime и Chrome.

В исследовании выбраны только технические способы принятых требований. Неразрешённых вопросов нет; новые ошибки/коды или поведение контракта не вводятся.
