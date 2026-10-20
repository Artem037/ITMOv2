## ADDED Requirements

### Requirement: Количество подписчиков по фильтру

Операция `count_subscribers(query="")` SHALL возвращать `int`, равный количеству имён для того же строкового запроса в `list_subscribers(query)`. Пустой запрос SHALL учитывать всех; пустой сервис и отсутствие совпадений SHALL давать `0`. Подсчёт SHALL сохранять множество `subscribers`, его объект и поведение существующих операций.

#### Scenario: Подсчёт с регистром и пробелами по краям
- **GIVEN** подписаны `"Ann"`, `"Anna"` и `"Bob"`
- **WHEN** вызван `count_subscribers(" aN ")`
- **THEN** результат равен `2` и имеет тип `int`, как количество имён в `["Ann", "Anna"]`

#### Scenario: Unicode сравнение
- **GIVEN** подписано имя `"Straße"`
- **WHEN** вызван `count_subscribers("STRASSE")`
- **THEN** результат равен `1`

#### Scenario: Пустой запрос считает всех
- **GIVEN** подписаны `"Ann"`, `"Anna"` и `"Bob"`
- **WHEN** подсчёт вызван без аргументов, с `""` или с `" \t\n"`
- **THEN** каждый вызов возвращает `3`

#### Scenario: Совпадений нет
- **GIVEN** подписано только имя `"Bob"`
- **WHEN** вызван `count_subscribers("zz")`
- **THEN** результат равен `0`

#### Scenario: Пустой сервис
- **GIVEN** подписчиков нет
- **WHEN** вызван `count_subscribers()` или `count_subscribers("ann")`
- **THEN** каждый вызов возвращает `0`

#### Scenario: Подсчёт сохраняет состояние и прежние вызовы
- **GIVEN** подписаны `"Ann"`, `"Anna"` и `"Bob"`, вызывающий сохранил ссылку на `subscribers`
- **WHEN** вызван `count_subscribers("ann")`
- **THEN** результат равен `2`, множество и его объект не изменились, `list_subscribers()` по-прежнему возвращает `["Ann", "Anna", "Bob"]`, а отписка `"Ann"` по-прежнему возвращает `{"unsubscribed": True}`
