# Мини-калькулятор заказа

Учебный проект для проверки code review в n8n. Только Node.js, без зависимостей.
Цены заданы в рублях; количество — положительное целое число.

```sh
make -C practices/practice_07/review-sandbox demo
make -C practices/practice_07/review-sandbox test
```

Ожидаемый результат demo: `total: 750`, `afterDiscount: 675`, `inStock: true`.
Три теста отдельно проверяют количество, скидку и точное совпадение остатка.
