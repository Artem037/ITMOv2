# Phase 1: модель данных и состояний

- **Snapshot**: полный валидированный PlanRequest одного датированного снимка (real по умолчанию, fixture по флагу старта), приватная копия приложения, не меняется; file/path не часть HTTP.
- **Metadata**: route{id,origin,destination,description?}, timezone, data_kind, schedule_dates, sources, defaults, limits; точная схема CONTRACT C-02.
- **Parameters**: departure_window{start,end}, boarding_buffer_minutes, max_options; строгая форма, целые 0–1440/1–5, ISO +03:00 с секундами, end>=start.
- **Request copy**: глубокая копия Snapshot с заменой только Parameters; обязательные parse_request → plan_departures.
- **PlanResult**: существующий TypedDict ядра, передаётся целиком; три статуса, options/warnings/sources/data_kind/search_scope. Fractional minutes сохраняются.
- **AdapterError**: status HTTP плюс error{code,message,field?}; field только известный форме, остаточная InputError общая, текст не парсится.
- **UI request state**: revision, sequence, snapshot of sent parameters; только последняя отправка текущей редакции может менять результат. Сервер эти ID не хранит.

Загрузка metadata → initial; редактирование → editing; неверный ввод → invalid; отправка → pending; актуальный ответ → success/no_routes/needs_data; сбой/таймаут → transport_error. Любое редактирование очищает текущий итог и обесценивает старую отправку. Таймаут 10 секунд без автоматического повтора; повтор одинаковой редакции во время pending блокируется. Подробности CONTRACT C-06; статусы UI не расширяют PlanResult.

schedule_dates содержит даты применимости только источников расписанных этапов, с учётом source_ids этапа и source_id рейсов. Полные sources сохраняют собственные valid_dates; карта30–31 октября не расширяет железнодорожное расписание30 октября. Источники/checked_at не меняются при вычислении.
