// Положительный заказ допустим, если товара хватает, включая точное равенство.
export function canFulfill(stock, quantity) {
  return stock > quantity;
}
