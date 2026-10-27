# Quickstart validation

Из корня репозитория на practice_05:

```sh
make -C practices/practice_04/homework install
make -C practices/practice_05/homework serve
```

Открыть http://127.0.0.1:8765. Для другого порта: make -C practices/practice_05/homework serve PORT=8766. Установка нужна только при отсутствии окружения ДЗ4; основной сценарий offline.

Проверки: `make step5`, `sh scripts/check.sh`, `make test`, `git diff --check`.
Браузерный инструмент требует Node, Playwright и Chromium/Chrome; пути и установка описываются в README ДЗ5. Он не является зависимостью запущенного приложения.

Наблюдения: исходный расчёт → 09:35–11:50/135; запас 20 → 09:25/145; окно 09:36–10:00 → no_routes; 15 октября → needs_data; обратное окно → ошибка → исправление → успех. Даты рейсов не меняются. Не использовать учебные времена для реальной поездки.
