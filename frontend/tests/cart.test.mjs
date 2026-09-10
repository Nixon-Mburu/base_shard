import test from "node:test";
import assert from "node:assert/strict";
import { normalizeCart, totals } from "../shared/catalog.mjs";
test("invalid and unknown items are discarded and stock is enforced", () => {
  assert.deepEqual(
    normalizeCart({ rice: 999, oil: -1, milk: 1.5, unknown: 4, tea: "2" }),
    { rice: 40 },
  );
  assert.deepEqual(normalizeCart(null), {});
});
test("totals calculate quantities and delivery threshold", () => {
  assert.deepEqual(totals({}).total, 0);
  assert.equal(totals({ rice: 2, oil: 1 }).total, 9530);
  assert.equal(totals({ rice: 5 }).delivery, 0);
  assert.equal(totals({ rice: 2, oil: 1 }).count, 3);
});
