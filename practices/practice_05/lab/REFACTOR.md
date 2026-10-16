# Подготовительный рефакторинг Notify Mini

Исторический снимок кода `60e21d0`, до добавления фильтра. Указанные ниже 12 тестов демо и 46 общих тестов относятся к этому снимку. Текущая фича, её 17 тестов демо и итоговые 51 тест описаны в [REPORT.md](REPORT.md).

Выполнен spec-driven рефакторинг нашего сервиса подписки: действующее поведение описано в OpenSpec, одинаковая нормализация имени вынесена в одну функцию, совместимость проверена до и после изменения. Пользователь подтвердил выбор Notify Mini: преподаватель разрешил брать свой проект для персонализации.

## Что изменилось

`service.py` использует приватную `_normalize_name(name: str) -> str` в подписке и отписке. Общий объект `subscribers`, публичные функции, словари результатов и хранение в памяти сохранены. Добавлены четыре проверки публичного контракта; теперь в демо 12 тестов.

Работа выполнена в корне `/Users/pip/ITMOv2`, в ветке `practice-05`. OpenSpec — `1.14.1`, профиль `core`, интеграции Codex и OpenCode. Домашняя работа 5 и третья User Story в этот этап не входят.

## Как пройден SDD

1. **Контекст:** прочитаны AGENTS, код, тесты, README, Makefile и STYLE_GUIDE. Исходный runner прошёл 8 тестов демо, 28 тестов домашки 4 и 6 тестов hook: [baseline](evidence/baseline.txt).
2. **Specify:** в [основной spec](../../../openspec/specs/notify-mini/spec.md) зафиксирован уже действующий контракт. [Proposal](../../../openspec/changes/notify-mini-name-normalization/proposal.md), [design](../../../openspec/changes/notify-mini-name-normalization/design.md) и [tasks](../../../openspec/changes/notify-mini-name-normalization/tasks.md) описывают изменение.
3. **Уточнение:** выбран чистый рефакторинг. CLI требует `skip_specs: true` для изменения без новых требований; delta specs не создавались. Локальный запуск — работа существующего модуля в одном Python-процессе. Это фактический формат демонстрации; решение о зачёте остаётся у преподавателя.
4. **Проверки до кода:** новые четыре теста прошли на старой реализации: [12 тестов до рефакторинга](evidence/before-refactor.txt), коммит `da2f092`. Это characterization tests; не заявляем, что наблюдалось RED для отсутствующей новой функции.
5. **Рефакторинг:** извлечена общая нормализация, снова прошли 12 тестов демо и общий runner: [результат](evidence/after-refactor.txt). Коммит кода — `60e21d0`; pre-commit Ruff и тесты также прошли.
6. **Локальный запуск:** в настоящем интерактивном Python показаны нормализация, повторная подписка, сортировка, повторная отписка и ошибка пустого имени. После ошибки Zoe осталась в состоянии; новый процесс начал с пустого списка: [транскрипт](evidence/demo.txt).

## Связь требований с проверками

| Требование | Проверка |
| --- | --- |
| Пробелы по краям удаляются | `test_subscribe_trims_name`, `test_unsubscribe_removes_existing` |
| Пустое имя не меняет непустое состояние | `test_empty_names_preserve_existing_subscribers` |
| Повторная подписка не создаёт дубликат | `test_duplicate`; одинаковый ответ двух подписок также показан в демо |
| Повторная отписка безопасна | `test_repeated_unsubscribe_returns_false`, `test_unsubscribe_missing_is_safe` |
| Список отсортирован и не меняет множество | `test_list_subscribers_sorted_without_mutation`, `test_list_subscribers_empty` |
| Возвращённый список независим | `test_list_result_is_detached` |
| Импортированная ссылка на состояние сохранена | `assertIs(service.subscribers, subscribers)` в `test_subscribe_trims_name` |
| Состояние существует только в текущем процессе | REPL и отдельный новый процесс в `evidence/demo.txt` |

## Официальная документация через MCP

Реально выполнен MCP stdio `initialize → list_tools → tools/call`, инструмент `fetch`, через сервер, указанный в `opencode.json`. Использован существующий locked MCP SDK; LLM для получения страниц не запускалась.

- [str.strip](https://docs.python.org/3/library/stdtypes.html#str.strip) без `chars` удаляет пробельные символы по краям строки. Вызов: `fetch({"url":"https://docs.python.org/3/library/stdtypes.html","start_index":95286,"max_length":1300,"raw":false})`.
- [set.discard](https://docs.python.org/3/library/stdtypes.html#set.discard) удаляет элемент, если он присутствует; повторная отписка не требует `remove` и обработки `KeyError`. Вызов: `fetch({"url":"https://docs.python.org/3/library/stdtypes.html","start_index":189532,"max_length":350,"raw":false})`.

Точные ответы, метаданные подключения и предупреждения первого получения страницы сохранены в [MCP evidence](evidence/python-docs-mcp.txt). Проверочные вызовы завершились с `isError: false`; метка о пагинации — ограничение длины возвращённого текста.

## Как показать из корня

Проверить подготовленную среду:

```sh
node --version
openspec --version
openspec list --json
openspec status --change notify-mini-name-normalization
```

Запустить модуль:

```sh
python3 -i practices/practice_03/lab/demo/service.py
```

В одном интерактивном процессе выполнить:

```python
list_subscribers()       # []
subscribe(" Ann ")      # {'subscribed': True}
subscribe("Ann")        # {'subscribed': True}
subscribe("Zoe")        # {'subscribed': True}
list_subscribers()       # ['Ann', 'Zoe']
unsubscribe(" Ann ")    # {'unsubscribed': True}
unsubscribe("Ann")      # {'unsubscribed': False}
subscribe(" \t\n")      # ValueError: empty name
list_subscribers()       # ['Zoe']
exit()
```

Для объяснения на занятии: «Сначала мы записали проверяемое поведение существующего проекта. Затем защитили важные случаи тестами, убрали повтор кода и показали тот же результат в работающем локальном процессе».

## Итоговая приёмка

Независимое ревью и итоговые команды фиксируются в [review](evidence/review.md) и [checks](evidence/checks.txt). Чекбоксы OpenSpec отражают выполнение задач, но не подтверждают оценку преподавателя. Change остаётся доступен для просмотра до пользовательской приёмки; при последующем архивировании синхронизация delta не нужна, поскольку поведение не менялось.
