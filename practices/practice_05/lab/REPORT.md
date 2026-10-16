# Практика 5 Фильтр подписчиков Notify Mini

Небольшая фича для нашего проекта: `list_subscribers(query="")` умеет искать подписчиков по части имени. Запрос не учитывает регистр и пробельные символы по краям. Имена, подписки, сортировка и старый вызов без аргументов сохраняются.

## Пять условий

1. Подстрока ищется без учёта регистра, включая Unicode caseless matching.
2. Пробельные символы по краям запроса удаляются.
3. Пустой или пробельный запрос возвращает весь список.
4. Отсутствие совпадений и пустой сервис дают `[]`.
5. Результат отсортирован и независим от состояния; хранимые имена не меняются.

## Как выполнен OpenSpec цикл

Все команды выполнялись из `/Users/pip/ITMOv2`, ветка `practice-05`, OpenSpec `1.14.1`. Использован текущий Codex; профиль `core` также настроен для OpenCode.

- **Explore:** прочитаны код, README, тесты и текущая spec. Уже был отсортированный список без параметров; выбрана одна маленькая фича для своего проекта, как уточнил пользователь по материалам преподавателя. Baseline — [12 успешных тестов](evidence/filter-baseline.txt).
- **Proposal:** создан change `filter-notify-mini-subscribers` с [обоснованием](../../../openspec/changes/filter-notify-mini-subscribers/proposal.md).
- **Требования и обсуждение:** пять условий и конкретные входы/выходы сохранены в [delta spec](../../../openspec/changes/filter-notify-mini-subscribers/specs/notify-mini/spec.md), решения — в [design](../../../openspec/changes/filter-notify-mini-subscribers/design.md), действия — в [tasks](../../../openspec/changes/filter-notify-mini-subscribers/tasks.md).
- **RED:** до реализации добавлены пять тестов. [Фактический прогон](evidence/filter-red.txt) дал 6 ошибок `TypeError` на отсутствующем параметре: у одного теста два subtest. Старые 12 тестов прошли.
- **GREEN:** функция получила необязательный `query`, очистку запроса и фильтрацию перед `sorted`. [Все 17 тестов прошли](evidence/filter-green.txt); README содержит пример новой функции и старого вызова.
- **Локальный показ:** настоящий интерактивный Python запущен из корня; [вывод](evidence/filter-demo.txt) показывает все пять условий и неизменный полный список.
- **Проверка:** [независимое ревью](evidence/filter-review.md), [итоговые команды и вывод](evidence/filter-checks.txt). Архивирование и sync delta остаются после пользовательской приёмки.

Подготовительный рефакторинг вынес нормализацию имени в один helper; его отдельные доказательства сохранены в [REFACTOR.md](REFACTOR.md). Он не заменяет фичу фильтра, выбранную для занятия.

## Требование и тест

| Условие | Тест |
| --- | --- |
| Подстрока, регистр и Unicode, исходное написание | `test_list_filters_substring_without_case` |
| Пробелы по краям запроса | `test_list_filter_trims_query` |
| Пустой и пробельный запрос | `test_list_filter_blank_query_returns_all` |
| Нет совпадений и пустой сервис | `test_list_filter_without_matches_returns_empty` |
| Состояние, сортировка и независимость результата | `test_list_filter_preserves_state` и прежние тесты списка |
| Совместимость подписки, отписки и списка без аргументов | Все прежние 12 тестов |

Для выбора сравнения реально вызван MCP `fetch({"url":"https://docs.python.org/3/library/stdtypes.html","start_index":64264,"max_length":750,"raw":false})`. Официальный [str.casefold](https://docs.python.org/3/library/stdtypes.html#str.casefold) предназначен для caseless matching: `straße` становится `strasse`, в отличие от `lower`. [Фактический ответ MCP](evidence/filter-python-docs-mcp.txt) имеет `isError: false`.

## Как показать из корня

```sh
openspec --version
openspec status --change filter-notify-mini-subscribers
python3 -i practices/practice_03/lab/demo/service.py
```

Затем в Python:

```python
subscribe("Anna")
subscribe("Bob")
subscribe("Ann")
list_subscribers(" aN ")  # ['Ann', 'Anna']
list_subscribers("zz")    # []
list_subscribers("   ")  # ['Ann', 'Anna', 'Bob']
list_subscribers()        # ['Ann', 'Anna', 'Bob']
exit()
```

Проверка из корня: `sh scripts/check.sh`, затем `git diff --check` и `openspec validate --all --strict`. Итоговый состав: 17 тестов демо + 28 домашки 4 + 6 hook = 51 тест.

Это локальный Python-модуль со состоянием в процессе. HTTP-сервер, БД, отдельный интерфейс и домашняя работа 5 не добавлялись; оценка преподавателя не утверждается.
