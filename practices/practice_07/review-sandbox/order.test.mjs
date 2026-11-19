import assert from 'node:assert/strict';
import test from 'node:test';
import { cartTotal } from './cart.mjs';
import { applyDiscount } from './discount.mjs';
import { canFulfill } from './stock.mjs';

test('стоимость учитывает количество каждой позиции', () => {
  assert.equal(cartTotal([{ price: 250, quantity: 3 }]), 750);
});

test('скидка 10% уменьшает 1000 до 900', () => {
  assert.equal(applyDiscount(1000, 10), 900);
});

test('заказ разрешён, когда остаток равен количеству', () => {
  assert.equal(canFulfill(3, 3), true);
});
