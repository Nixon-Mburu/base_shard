export const money = (value) =>
  new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    maximumFractionDigits: 0,
  }).format(value);
export function normalizeCart(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(
      ([id, n]) =>
        id.length <= 80 && Number.isInteger(n) && n > 0 && n <= 10000,
    ),
  );
}
export function cartCount(cart) {
  return Object.values(normalizeCart(cart)).reduce((s, n) => s + n, 0);
}
export function totals(cart, products = []) {
  const items = products
    .filter((p) => cart[p.id])
    .map((p) => ({ ...p, quantity: cart[p.id] }));
  const subtotal = items.reduce((s, p) => s + p.price * p.quantity, 0);
  const delivery = subtotal === 0 || subtotal >= 15000 ? 0 : 350;
  return {
    items,
    subtotal,
    delivery,
    total: subtotal + delivery,
    count: cartCount(cart),
  };
}
