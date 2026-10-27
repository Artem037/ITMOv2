# HTTP contract reference

Канонический принятый договор: [CONTRACT 1.0](../../../practices/practice_05/homework/CONTRACT.md), C-01–07. Приёмка: [AGREEMENT](../../../practices/practice_05/homework/AGREEMENT.md), 27.10.2026, checkpoint 91994f0.

GET /api/trip → Metadata; POST /api/plan → полный PlanResult без обёртки. Ошибки отдельно. Никакого нового контракта этим файлом не вводится. Примеры настоящего ядра: [contract-examples.json](../../../practices/practice_05/homework/evidence/contract-examples.json).

Конституционные проверки: один снимок/копия на вызов, loopback, без shell/path/сети, неизменные CLI/MCP. Проверки контракта — tests/test_adapter.py; пользовательского состояния и интеграции — tests/browser.test.mjs.
