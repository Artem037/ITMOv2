# Отчёт: локальные модели

Отчёт ведёт OpenCode по фактическим результатам команд и вашим сообщениям в чате. Поручите агенту заполнить разделы и показать diff. Выводы студента он записывает после обсуждения; отсутствующие измерения отмечает как невыполненные.

## Окружение

ОС / CPU / GPU / RAM:
- macOS 26.5.1
- Apple M5, 10 ядер (4 производительных, 6 энергоэффективных)
- GPU: Apple M5 (встроенная), дисплей 2560×1664
- RAM: 16 GB
- Свободное место на диске: 317 GiB (df -h /)
- Apple Silicon использует unified memory, отдельная VRAM не указана.

Версии инструментов:
- Ollama: 0.34.4
- OpenCode: 1.18.32
- Python: 3.14.5

Скачанные и использованные модели:
- qwen3.5:4b (ID: 2a654d98e6fb; Weights SIZE: ~3.4 GB)
- itmo-agent (ID: 3465bc38f59d; Weights SIZE: ~3.4 GB; Loaded model SIZE ~5.6 GB per ollama ps)
- itmo-local (ID: 506b2ead5302; Weights SIZE: ~3.4 GB)
- itmo-local-relaxed (ID: a07fb0704834; Weights SIZE: ~3.4 GB)

Формат, квантизация, лицензия, источник:
- Семейство: Qwen3.5, параметры ~4.7B, формат GGUF, квантизация: Q4_K_M
- Лицензия: Apache-2.0
- Источник: Ollama, локально загружено

Фактический контекст и размещение:
- itmo-agent: num_ctx 65536 (ollama show itmo-agent)
- ollama ps: активная модель присутствует
  - NAME: itmo-agent:latest; CONTEXT: 65536; SIZE: 5.6 GB; PROCESSOR: 100% GPU; UNTIL: 4 minutes from now
  - Ответ модели на READY: READY

Почему выбрана эта конфигурация:
- Соответствует требованиям практики, 4B-вариант укладывается в 16 GB RAM, обеспечивает приемлемую скорость на CPU/GPU Apple.

## Сравнение семейств

| Разработчик / модель | Задача | Параметры / формат | Лицензия | Язык / tools | Источник |
|---|---|---|---|---|---|
| Qwen / Qwen3.5-4B | Text generation | 4.66–4.7B, GGUF/Q4_K_M | Apache-2.0 | русский: не подтверждено; tools: подтверждено | https://ollama.com/library/qwen3.5:4b |
| Google / Gemma 2 2B | Text generation, text-to-text | 2B, Safetensors | Gemma | русский: не подтверждено; tools: не подтверждено | https://huggingface.co/google/gemma-2-2b |

## Воспроизведение

Команды и файлы конфигурации:
- Сборка и тесты учебного проекта: make -C practices/practice_03/lab install; make -C practices/practice_03/lab test
- Создание и запуск локальных моделей в Ollama согласно Modelfile/Modelfile.agent
- Конфигурация OpenCode для демо: lab/demo/opencode.json (разрешён только локальный провайдер Ollama; reasoningEffort: none; агент local-guide read-only)

Подтверждение локального endpoint и скачанных весов:
- ollama list, ollama show qwen3.5:4b, ollama show itmo-agent
- opencode debug config, opencode models — модель и small_model: ollama/itmo-agent; плагины отсутствуют; доступна только ollama/itmo-agent

Проверка без сети после подготовки:
- Выполнена вручную: Wi‑Fi был отключён человеком.
- Ollama запущен с отключёнными cloud-функциями (OLLAMA_NO_CLOUD=1) в единственном серверном процессе.
- Локальный endpoint: http://localhost:11434
- Команда проверки: bash practices/practice_03/lab/offline-check.sh
- Точный тег модели: qwen3.5:4b
- Краткий ответ: OK
- Результат: practices/practice_03/lab/results/offline-check.json

Если работали в паре, чей компьютер и почему:
- Не применимо.

## Эксперимент

Фактор A/B:
- Baseline vs System (system.txt)
Неизменные условия:
- Одна модель, один вопрос, temperature=0.2, seed=42, think=false.
| Вопрос | Эталон и file:line | Ответ A | Ответ B | Верно A/B | Наблюдение инструментов |
|---|---|---|---|---|---|
| CI-система в проекте | demo/README.md | Baseline добавил неподтверждённые предположения и нарушил формат | System признал отсутствие данных, дал основание | Верно: System | — |

Ссылки на результаты:
- lab/results/baseline.json
- lab/results/system.json

Температурный эксперимент (этапы 40–50)

Во всех шести ответах модель правильно признала отсутствие сведений о CI, не выдумала конкретную CI-систему, привела основание из README и соблюла формат «короткий ответ, затем основание».

При temperature=0.2 и 0.8 содержательная вариативность оказалась минимальной: различались главным образом формулировки основания. Повышение temperature до 0.8 на этом наборе не привело к фактическим ошибкам или галлюцинациям.

Ссылки на шесть JSON:
- lab/results/low42.json
- lab/results/low43.json
- lab/results/low44.json
- lab/results/hot42.json
- lab/results/hot43.json
- lab/results/hot44.json

Таблица медиан (по трём прогретым запускам; warmup не учитывались):

| temperature | median wall_seconds | median load_seconds | median total_seconds | median decode_tokens_per_second |
|-------------|---------------------:|--------------------:|---------------------:|--------------------------------:|
| 0.2         | 16.376087750002625   | 0.005047459         | 16.172395625         | 9.383841734661477               |
| 0.8         | 31.557288000010885   | 0.00453625          | 31.346662958         | 9.988596352497565               |

A/B — Modelfile (strict vs relaxed)

При одинаковых весах qwen3.5:4b, temperature=0.2, seed=42, num_ctx=4096 и одинаковом вопросе изменение только SYSTEM заметно изменило поведение модели.

Наблюдения:
- Строгая конфигурация itmo-local ограничилась фразой об отсутствии ответа и не стала строить предположения.
- Ослабленная конфигурация itmo-local-relaxed предложила варианты как «Предположение», не выдавая их за факт.

Ссылки на результаты:
- lab/results/modelfile-strict.json
- lab/results/modelfile-relaxed.json

Названия моделей:
- itmo-local
- itmo-local-relaxed

Команды воспроизведения моделей (strict/relaxed):
- Создание строгой модели:
  ollama create itmo-local -f practices/practice_03/lab/Modelfile.strict
- Создание ослабленной модели:
  ollama create itmo-local-relaxed -f practices/practice_03/lab/Modelfile.relaxed
- Проверка конфигураций:
  ollama show itmo-local --modelfile
  ollama show itmo-local-relaxed --modelfile

## Скорость

Холодный старт отдельно:
- Учитывался отдельно, warmup не включался в медианы.
- Ссылки: lab/results/warmup-low.json; lab/results/warmup-hot.json
- Фактические warmup метрики:
  - warmup-low.json: wall_seconds=16.071840375; load_seconds=4.617592083; total_seconds=16.041715416; decode_tokens_per_second=10.234728044
  - warmup-hot.json: wall_seconds=11.316204417; load_seconds=4.618134083; total_seconds=11.267254875; decode_tokens_per_second=10.863122380
Три прогретых повтора и медиана:
- temperature=0.2: median decode_tokens_per_second ≈ 9.38
- temperature=0.8: median decode_tokens_per_second ≈ 9.99
Единицы и метод замера:
- Метрики из файлов результатов: wall_seconds, load_seconds, total_seconds, decode_tokens_per_second; медиана по трём прогретым повторениям.
TTFT измерен или не измерен:
- Не измерен (скрипт не потоковый).

Ссылка на первый запрос и краткий результат:
- practices/practice_03/lab/results/first-query.txt — «Сервер — это ... Модель же ...»

## Вывод

Ошибка или обнаруженное ограничение:
- В baseline появились неподтверждённые предположения; в вопросе о сохранении подписок модель прочитала нерелевантный opencode.json вместо service.py и README.md.
Как проверили:
- Сопоставление ответов с кодом и README; make test подтвердил ожидаемое поведение.
Какой конфигурацией будете пользоваться:
- Для репозитория — строгий system prompt (system mode) с temperature=0.2; для генерации гипотез — relaxed SYSTEM.
Что осталось непроверенным:
- В рамках практики обязательные проверки выполнены.

Пояснения по инструкциям и модели:
- SYSTEM в Modelfile встраивается в созданную модель.
- system.txt передаётся experiment.py только в режиме system.
- repo-system.txt является инструкцией агента local-guide и регулирует работу с инструментами.
- Изменение инструкций не обучает и не изменяет веса модели.
- Ошибка в вопросе о сохранении подписок связана с чтением нерелевантного opencode.json вместо service.py и README.md.
Проверка человеком (этап 65–80)

Исходные сохранённые ответы:
- lab/results/read-check.jsonl
- lab/results/question-2-empty-name.jsonl
- lab/results/question-3-unsubscribe.jsonl
- lab/results/question-4-ci.jsonl
- lab/results/question-5-persistence.jsonl

Проверка против фактического кода в каталоге demo:
1. Команда тестирования: «make test». Инструменты: read demo/README.md. Оценка: правильно. Подтверждение: demo/README.md, строка 6.
2. Пустое имя подписчика: ValueError("empty name"). Инструменты: read demo/service.py; read demo/test_service.py. Оценка: правильно. Подтверждение: demo/service.py, строки 4–7; demo/test_service.py, строки 13–15. Фактический вывод правильный, но приведённый фрагмент не полностью дословный.
3. Функция unsubscribe: не реализована. Инструменты: grep по каталогу demo. Оценка: правильно. Подтверждение: совпадений «unsubscribe» нет; в demo/service.py есть только subscribe.
4. CI-система: сведений о конкретной CI нет. Инструменты: glob/grep по файлам CI. Оценка: правильно. Подтверждение: файлов конфигурации CI нет.
5. Сохранение подписок после перезапуска: ответ неполный из-за чтения opencode.json; фактически подписки не сохраняются. Подтверждение: demo/README.md, строка 2; demo/service.py, строка 1.

Результат make test
```
Standard library only: ready
/Library/Developer/CommandLineTools/usr/bin/make -C demo test
python3 -m unittest -v
test_duplicate (test_service.SubscribeTest.test_duplicate) ... ok
test_empty (test_service.SubscribeTest.test_empty) ... ok
test_subscribe (test_service.SubscribeTest.test_subscribe) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.000s

OK
```
