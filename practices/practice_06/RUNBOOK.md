# Проверка ДЗ 6

Команды из корня репозитория. Магазин и проверки используют Python 3.10+
и стандартную библиотеку. Тесты и HTTP-replay не требуют LLM или сети.

```sh
make step6
make test
git diff --check
python3 practices/practice_06/scripts/replay_attacks.py --phase after --output /tmp/mini-shop-after.json
```

Replay запускает собственный сервер на свободном порту `127.0.0.1`, проверяет
21 сценарий и останавливает только свой процесс. Не запускать старые команды
на чужих сервисах и не заменять ограничение sandbox вызовом shell.

## Чистая база PR и сохранённые эксперименты

Ветка practice_06 подготовлена от origin/main (0c8a9c1), без локальных изменений
ДЗ 3–4. Дерево Mini Shop в этой базе совпадает с исторической e2e3315;
хеши исходников и сохранённые before/after evidence не переписывались.
Команды выше работают в чистом клоне с Python стандартной библиотеки.
Исторический runner scripts/check.sh относился к полному рабочему репозиторию
с ДЗ 4; он не переносится в этот PR и не нужен для make step6 / make test.

## Повтор исходных атак без смены ветки

Код исходного магазина берётся из опубликованной базы `0c8a9c1567e334a00502a2d83bd3d9997b2b2687`, а текущий replay копируется
в отдельный временный каталог. Текущий исправленный сервис не подменяется.

```sh
python3 - <<'PY'
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory(prefix="practice06-original-source-") as directory:
    root = Path(directory)
    (root / "lab").mkdir()
    (root / "scripts").mkdir()
    for name in ["service.py", "sandbox.py"]:
        source = subprocess.check_output([
            "git", "show", f"0c8a9c1567e334a00502a2d83bd3d9997b2b2687:practices/practice_06/lab/{name}"
        ])
        (root / "lab" / name).write_bytes(source)
    shutil.copyfile(
        "practices/practice_06/scripts/replay_attacks.py",
        root / "scripts/replay_attacks.py",
    )
    subprocess.run([
        sys.executable, str(root / "scripts/replay_attacks.py"),
        "--phase", "before", "--output", "/tmp/mini-shop-before.json",
    ], check=True)
PY
```

## Реальная модель

Рабочий эксперимент сохранён: `evidence/before/verified/` и
`evidence/after/verified/`. Четыре различные сессии, одна модель
`vsellm/openai/gpt-5`, неизменные system prompt, вопрос и атакующий отзыв.
Отдельные judge-запуски: before/review2 и after/verified.

Новый прогон требует настроенного провайдера. Для VseLLM передать существующий
`VSELLM_API_KEY` через окружение; не записывать его в Git, команды или evidence.
`--model` обязателен. Выбрать незанятый run ID, чтобы не перезаписать доказательства:

```sh
python3 practices/practice_06/scripts/run_model_checks.py --phase after --kind planner --model vsellm/openai/gpt-5 --run-id review2
```

Этот запуск обращается к внешнему провайдеру и отправляет только синтетический
контекст. Исходные бесплатные вызовы с лимитом находятся отдельно и не считаются
ответами модели. У planner и judge запрещены инструменты. Runtime overrides
отключают ненужные MCP/plugins и snapshots, не меняя разрешения агентов.
Источники конфигурации: [OpenCode config](https://opencode.ai/docs/config/),
[CLI](https://opencode.ai/docs/cli/).

Судье передаются два вложения: исходники/отчёт и форматированный JSON evidence.
Каждый файл ограничен 48 000 байтами и длиной строки, чтобы избежать усечения
при автоматическом чтении вложений. Сохраняются финальные ответы без reasoning.
Экспорты/удаление, изготовленные рабочим агентом, помечаются отдельно от LLM.
