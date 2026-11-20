# ДЗ 7.2 со звёздочкой

[Классификатор `7.2_1`](7.2_1.json) · [Обработка Issues `7.2_2`](7.2_2.json) · [Недельный отчёт `7.2_3`](7.2_3.json)

**Классификация.** В запуске #4017 основной сценарий вызвал классификатор. Запуск #4018 вернул `feature` с уверенностью `0.9`. Лейблы видны в [тестовом репозитории](https://github.com/Artem037/ITMOv2/issues) на [`bug` (#14)](https://github.com/Artem037/ITMOv2/issues/14), [`task` (#16)](https://github.com/Artem037/ITMOv2/issues/16) и [`feature-request` (#17)](https://github.com/Artem037/ITMOv2/issues/17).

![Запуск основного сценария #4017 с веткой feature-request](evidence/13-feature-request-execution.png)

![Запуск классификатора #4018](evidence/12-classifier-execution.png)

![Выход классификатора с типом и уверенностью](evidence/11-classifier-output.png)

![Лейбл task и автоответ на Issue №16](evidence/03-task-issue.png)

![Лейбл feature-request и автоответ на Issue №17](evidence/04-feature-request-issue.png)

**Ручная проверка Issue.** Для Issue #15 классификатор вернул `unknown` с уверенностью `0.5`. В GitHub появился `needs-triage`, комментариев нет. [Issue #15](https://github.com/Artem037/ITMOv2/issues/15)

![Запуск #4010 в Executions](evidence/01-needs-triage-execution.png)

![Выход ноды «Маршрут» с confidence 0.5 и route unknown](evidence/14-needs-triage-output.png)

![Выполнение ветки needs-triage в n8n](evidence/15-needs-triage-branch.png)

![Лейбл needs-triage без автоответа в Issue №15](evidence/02-needs-triage-issue.png)

**Повторная доставка.** Запуск #4020 остановился на проверке `processed_issues`.

![Таблица processed_issues с четырьмя обработанными Issues](evidence/05-processed-issues.png)

![Повторный запуск #4020 остановился на проверке таблицы](evidence/06-deduplication-execution.png)

**Еженедельный отчёт.** В `7.2_3` задан Cron `0 9 * * MON`. Ручной запуск #5627 выполнил четыре запроса к GitHub и отправил HTML-письмо через Gmail SMTP.

![Запуск отчёта #5627 в Executions](evidence/07-weekly-report-run.png)

![Полученное письмо со сводкой и разбивкой по типам](evidence/09-email-report.png)

**Звёздочка.** В `weekly_issue_stats` есть демонстрационная запись за неделю с 9 ноября и статистика, сохранённая n8n за неделю с 16 ноября. В письме показана Δ по четырём метрикам (`+2`, `−1`, `+3`, `+1`) и комментарий модели.

![Две недели в таблице weekly_issue_stats](evidence/08-weekly-issue-stats.png)

![Разбивка по автору, сравнение недель и AI-комментарий](evidence/10-email-delta-ai.png)
