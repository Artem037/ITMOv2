// Скидка percent (0..100) должна уменьшать исходную сумму total.
export function applyDiscount(total, percent) {
  return total - total * percent / 100;
}
