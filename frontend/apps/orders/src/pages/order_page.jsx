import React, { useState } from "react";
import {
  Search,
  ArrowRight,
  Truck,
  ShieldCheck,
  Package,
  SlidersHorizontal,
  Plus,
  ShoppingBag,
} from "lucide-react";
import { products, money, totals } from "../../../../shared/catalog.mjs";
import { useCart, useStore } from "../../../../shared/store";
import ProductArt from "../../../../shared/ProductArt";
import "../styles/order_page.css";
export default function Orders({ navigate }) {
  const [cart, setCart] = useCart();
  const [merchant] = useStore("merchant", null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All products");
  const [sort, setSort] = useState("popular");
  const [error, setError] = useState("");
  const categories = [
    "All products",
    ...new Set(products.map((p) => p.category)),
  ];
  const summary = totals(cart);
  const filtered = products
    .filter(
      (p) =>
        (category === "All products" || p.category === category) &&
        p.name.toLowerCase().includes(query.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "low"
        ? a.price - b.price
        : sort === "high"
          ? b.price - a.price
          : 0,
    );
  function change(p, delta) {
    const next = {
      ...cart,
      [p.id]: Math.max(0, Math.min(p.stock, (cart[p.id] || 0) + delta)),
    };
    try {
      setCart(next);
      setError("");
    } catch {
      setError(
        "Your browser could not save the basket. Enable local storage and try again.",
      );
    }
  }
  return (
    <div className="page orders-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR NEXT RESTOCK STARTS HERE</div>
          <h1>Good business starts with great stock.</h1>
          <p className="muted">
            Everything your business needs. Wholesale prices. One delivery.
          </p>
        </div>
      </div>
      <section className="restock-banner">
        <div>
          <span className="banner-kicker">
            <span /> STOCK UP. STRESS LESS.
          </span>
          <h2>
            Big on essentials.
            <br />
            Better for your business.
          </h2>
          <p>Keep your shelves full and your business moving.</p>
          <button
            className="btn primary small"
            onClick={() => document.getElementById("catalog-search").focus()}
          >
            Explore inventory <ArrowRight size={15} />
          </button>
        </div>
        <div className="banner-art" aria-hidden="true">
          <div className="parcel parcel-back">
            <span>base grid.</span>
          </div>
          <div className="parcel parcel-front">
            <Package size={33} />
            <strong>
              Good things
              <br />
              inside.
            </strong>
            <span>BASE GRID</span>
          </div>
          <div className="delivery-sticker">
            <Truck size={18} />
            <div>
              At your doorstep<small>Ready for your next chapter</small>
            </div>
          </div>
          <span className="spark spark-one">✦</span>
          <span className="spark spark-two">✦</span>
        </div>
      </section>
      <div className="benefits">
        <span>
          <Truck size={17} />
          <strong>Doorstep delivery</strong>
          <span>We do the heavy lifting</span>
        </span>
        <span>
          <ShieldCheck size={17} />
          <strong>Quality you can trust</strong>
          <span>Selected for your business</span>
        </span>
        <span>
          <Package size={17} />
          <strong>Wholesale value</strong>
          <span>More stock, better margins</span>
        </span>
      </div>
      <div className="catalog-header">
        <div>
          <h2>
            Shop inventory <span>{products.length} products</span>
          </h2>
          <p className="muted">Your everyday essentials, all in one place.</p>
        </div>
        <label className="search-box">
          <Search size={17} />
          <input
            id="catalog-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search inventory…"
            aria-label="Search inventory"
          />
        </label>
      </div>
      <div className="catalog-toolbar">
        <div className="category-tabs" aria-label="Product categories">
          {categories.map((c) => (
            <button
              key={c}
              className={c === category ? "selected" : ""}
              onClick={() => setCategory(c)}
              aria-pressed={c === category}
            >
              {c}
            </button>
          ))}
        </div>
        <label className="sort-control">
          <SlidersHorizontal size={15} />
          <select
            aria-label="Sort products"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="popular">Featured</option>
            <option value="low">Price: low to high</option>
            <option value="high">Price: high to low</option>
          </select>
        </label>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="product-grid">
        {filtered.map((p) => (
          <article className="product-card" key={p.id}>
            <div className="product-visual">
              {p.tag && <span className="product-tag">{p.tag}</span>}
              <ProductArt product={p} />
            </div>
            <div className="product-details">
              <span className="product-category">{p.category}</span>
              <h3>{p.name}</h3>
              <p className="product-unit">{p.unit}</p>
              <div className="product-bottom">
                <div>
                  <strong>{money(p.price)}</strong>
                  <span>
                    per{" "}
                    {p.unit.includes("bag")
                      ? "bag"
                      : p.unit.includes("bale")
                        ? "bale"
                        : "pack"}
                  </span>
                </div>
                {cart[p.id] ? (
                  <div className="quantity">
                    <button
                      aria-label={"Decrease " + p.name}
                      onClick={() => change(p, -1)}
                    >
                      −
                    </button>
                    <span aria-live="polite">{cart[p.id]}</span>
                    <button
                      aria-label={"Increase " + p.name}
                      disabled={cart[p.id] >= p.stock}
                      onClick={() => change(p, 1)}
                    >
                      +
                    </button>
                  </div>
                ) : (
                  <button
                    className="add-button"
                    onClick={() => change(p, 1)}
                    aria-label={"Add " + p.name}
                  >
                    <Plus size={15} /> Add
                  </button>
                )}
              </div>
              <div className="stock-label">
                <span /> In stock · {p.stock} available
              </div>
            </div>
          </article>
        ))}
      </div>
      {!filtered.length && (
        <div className="empty">
          <Search size={28} />
          <h2>No matching products</h2>
          <p className="muted">Try another search or category.</p>
          <button
            className="btn"
            onClick={() => {
              setQuery("");
              setCategory("All products");
            }}
          >
            Clear filters
          </button>
        </div>
      )}
      <div className="catalog-footnote">
        <ShieldCheck size={15} /> Carefully selected essentials. Transparent
        pricing. No surprises.
      </div>
      {summary.count > 0 && (
        <div className="basket-bar">
          <div className="basket-icon">
            <ShoppingBag size={21} />
          </div>
          <div>
            <strong>
              {summary.count} {summary.count === 1 ? "item" : "items"} in your
              order
            </strong>
            <small>
              {summary.subtotal >= 15000
                ? "Your order qualifies for free delivery"
                : money(15000 - summary.subtotal) + " away from free delivery"}
            </small>
          </div>
          <strong className="basket-total">{money(summary.subtotal)}</strong>
          <button className="btn primary" onClick={() => navigate("/checkout")}>
            Review order <ArrowRight size={16} />
          </button>
        </div>
      )}
      {!merchant && (
        <p className="setup-prompt">
          New here?{" "}
          <button className="link-button" onClick={() => navigate("/signup")}>
            Set up your business
          </button>{" "}
          for a smooth first delivery.
        </p>
      )}
    </div>
  );
}
