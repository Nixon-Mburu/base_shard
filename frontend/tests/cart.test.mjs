import test from "node:test";
import assert from "node:assert/strict";
import { normalizeCart, cartCount, totals } from "../shared/catalog.mjs";
test("basket keeps valid intent and removes invalid quantities", () => {
  assert.deepEqual(normalizeCart({ rice: 2, oil: -1, milk: 1.5, tea: "2" }), {
    rice: 2,
  });
  assert.deepEqual(normalizeCart(null), {});
  assert.equal(cartCount({ rice: 2, oil: 3 }), 5);
});
test("display totals use API products and quantities", () => {
  const products = [
    { id: "rice", price: 3450 },
    { id: "oil", price: 2280 },
  ];
  assert.equal(totals({ rice: 2, oil: 1 }, products).total, 9530);
  assert.equal(totals({ rice: 5 }, products).delivery, 0);
});
