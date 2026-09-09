# Integration-проверки

| ID / связь компонентов | Что может сломаться | Как воспроизводим | Ожидаемый результат | Evidence |
|---|---|---|---|---|
| `IT-API-LLM-1`: FastAPI → service → LLM-spy | Валидный запрос не доходит до adapter или ответ теряет структуру. | `TestClient` отправляет небольшой diff; spy возвращает валидный `OUT-1`. | HTTP 200; есть `summary`, `risks`, `checks`; spy вызван один раз. | Status, response schema, call count. |
| `IT-API-1`: validator → endpoint | Большой diff всё же вызывает дорогую зависимость. | Отправить 20 001 символ с LLM-spy. | HTTP 413; call count spy = 0. | Status и отсутствие вызова. |
| `IT-SEC-1`: redactor → LLM adapter | Секрет редактируется после внешнего вызова. | Передать маркерный token/private key и перехватить prompt spy-компонентом. | Во входе spy есть `[REDACTED]`, исходного секрета нет. | Captured prompt. |
| `IT-REL-1`: service → slow/failing LLM | Запрос зависает или исключение выходит наружу. | Stub ждёт >10 сек; второй stub выбрасывает исключение. | Timeout прекращается ≤10 сек и даёт 504; прочая ошибка даёт 502; тела не раскрывают diff. | Fake clock, статусы и schema error-response. |
| `IT-OUT-QA-1`: LLM → response validator | Невалидный или недоказанный вывод возвращается пользователю. | Stub возвращает 4 риска, неизвестную строку либо поле `comment`. | Ответ отклонён/нормализован по принятому контракту; недоказанные риски не выдаются как подтверждённые. | Response и validation event. |
| `IT-OBS-1`: pipeline → logger | Diff или ответ попадает в лог на успехе/ошибке. | Capture logs с маркерными значениями в diff и LLM response. | Есть только `request_id`, duration, status; маркеры отсутствуют. | Captured log records. |

## Как использовали AI

- Для чего: проверить именно границы между endpoint, сервисом, redactor, adapter, validator и logger.
- Тип промпта: homework master prompt.
- Строка в [`prompts.md`](prompts.md): `P1-03`.
- Что проверили и исправили сами: для каждого сценария добавили наблюдаемый evidence и проверку, что LLM не вызывается при раннем отказе.
