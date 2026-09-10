import { useEffect, useState } from "react";
import { normalizeCart } from "./catalog.mjs";
export function read(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem("base-grid:" + key)) ?? fallback;
  } catch {
    return fallback;
  }
}
export function write(key, value) {
  localStorage.setItem("base-grid:" + key, JSON.stringify(value));
  window.dispatchEvent(new Event("base-grid:change"));
}
export function useStore(key, fallback) {
  const [value, setValue] = useState(() => read(key, fallback));
  useEffect(() => {
    const update = () => setValue(read(key, fallback));
    window.addEventListener("storage", update);
    window.addEventListener("base-grid:change", update);
    return () => {
      window.removeEventListener("storage", update);
      window.removeEventListener("base-grid:change", update);
    };
  }, [key]);
  return [value, (next) => write(key, next)];
}
export function useCart() {
  const [raw, set] = useStore("cart", {});
  return [normalizeCart(raw), set];
}
