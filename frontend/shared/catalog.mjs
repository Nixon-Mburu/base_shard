export const products = [
  {
    id: "rice",
    name: "Premium pishori rice",
    category: "Grains & staples",
    unit: "25 kg bag",
    price: 3450,
    stock: 40,
    icon: "rice",
    tag: "BESTSELLER",
    color: "#f4e5c9",
  },
  {
    id: "oil",
    name: "Pure vegetable oil",
    category: "Cooking essentials",
    unit: "10 L jerrycan",
    price: 2280,
    stock: 32,
    icon: "oil",
    tag: "GREAT VALUE",
    color: "#f2d676",
  },
  {
    id: "flour",
    name: "All-purpose wheat flour",
    category: "Grains & staples",
    unit: "12 × 2 kg bale",
    price: 1890,
    stock: 50,
    icon: "flour",
    color: "#e4c6a0",
  },
  {
    id: "sugar",
    name: "White granulated sugar",
    category: "Grains & staples",
    unit: "25 kg bag",
    price: 3650,
    stock: 25,
    icon: "sugar",
    color: "#eedce6",
  },
  {
    id: "milk",
    name: "Long-life whole milk",
    category: "Dairy & beverages",
    unit: "12 × 1 L carton",
    price: 1440,
    stock: 28,
    icon: "milk",
    tag: "POPULAR",
    color: "#c6dbea",
  },
  {
    id: "tea",
    name: "Kenyan black tea",
    category: "Dairy & beverages",
    unit: "12 × 250 g packs",
    price: 2160,
    stock: 35,
    icon: "tea",
    color: "#baceaa",
  },
  {
    id: "soap",
    name: "Multipurpose liquid soap",
    category: "Cleaning supplies",
    unit: "5 L container",
    price: 680,
    stock: 45,
    icon: "soap",
    color: "#b9dcd3",
  },
  {
    id: "tissue",
    name: "Everyday tissue rolls",
    category: "Cleaning supplies",
    unit: "40 roll bale",
    price: 980,
    stock: 20,
    icon: "tissue",
    color: "#ded1ed",
  },
];
export const money = (value) =>
  new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    maximumFractionDigits: 0,
  }).format(value);
export function normalizeCart(value) {
  return Object.fromEntries(
    products.flatMap((p) =>
      Number.isInteger(value?.[p.id]) && value[p.id] > 0
        ? [[p.id, Math.min(p.stock, value[p.id])]]
        : [],
    ),
  );
}
export function totals(cart) {
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
    count: items.reduce((s, p) => s + p.quantity, 0),
  };
}
