# P1-02: ревью с Master Prompt v1

## Prompt

Использован полный раздел [`Master Prompt v1`](prompts.md#master-prompt-v1). В запуск передан тот же [`TRAINING_PR.diff`](TRAINING_PR.diff), что и в `P1-01`; дополнительных фактов в чат не добавлялось.

## Output

```yaml
summary: "Добавлен POST /api/reviews, который передаёт payload['diff'] в ReviewService.review; сервис вставляет исходный diff в prompt LLM и возвращает {'comment': ...}."
risks:
  - file: "app/review_service.py"
    line: 14
    evidence: "prompt = f\"...\\n{diff}\" (SEC-1)"
    risk: "В показанном пути diff без редактирования секретов вставляется в prompt и уходит во внешний LLM; возможная утечка токенов/ключей."
  - file: "app/api.py"
    line: 10
    evidence: "return review_service.review(payload[\"diff\"]) (API-1)"
    risk: "В показанном пути нет проверки длины diff > 20 000 символов и возврата 413; большие входы не отклоняются."
  - file: "app/review_service.py"
    line: 16
    evidence: "return {\"comment\": answer} (OUT-1)"
    risk: "Ответ не соответствует целевой схеме (summary, risks, checks); нарушается контракт OUT-1."
checks:
  - "SEC-1: подать через POST /api/reviews diff с token=API_KEY_123 и перехватить prompt LLM-spy; текущий код передаст API_KEY_123 вместо [REDACTED], а исправленный должен скрыть token."
  - "API-1: отправить diff длиной 20 001 символ; текущий код вызовет LLM либо вернёт comment, а исправленный должен вернуть HTTP 413 без вызова LLM."
  - "OUT-1: отправить небольшой diff; текущий JSON содержит comment, а исправленный должен пройти schema summary/risks/checks с максимум тремя risks."
```

## Собственная проверка

- Рисков ровно три, что соответствует лимиту `OUT-1`.
- Строки 14, 10 и 16 относятся к добавленным строкам восстановленного содержимого файлов из diff.
- Каждый риск опирается одновременно на evidence из diff и правило `CASE.md`.
- Формулировка «в показанном пути» не делает выводов о middleware или коде вне diff.
- Результат не меняет код и не предлагает approve/merge.
