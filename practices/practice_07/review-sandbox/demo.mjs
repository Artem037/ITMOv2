import { cartTotal } from './cart.mjs';
import { applyDiscount } from './discount.mjs';
import { canFulfill } from './stock.mjs';

const total = cartTotal([{ price: 250, quantity: 3 }]);
console.log({
  total,
  afterDiscount: applyDiscount(total, 10),
  inStock: canFulfill(3, 3),
});
