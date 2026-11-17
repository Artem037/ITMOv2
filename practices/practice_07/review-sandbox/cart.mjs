// Стоимость корзины — сумма price * quantity для каждой позиции.
export function cartTotal(items) {
  return items.reduce((total, item) => total + item.price * item.quantity, 0);
}
