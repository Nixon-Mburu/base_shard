import React, { useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  MapPin,
  Truck,
  ShieldCheck,
  Smartphone,
  Wallet,
  ShoppingBag,
} from "lucide-react";
import { useCart, useStore, write } from "../../../../shared/store";
import { totals, money } from "../../../../shared/catalog.mjs";
import ProductArt from "../../../../shared/ProductArt";
import "../styles/checkout_page.css";
export default function Checkout({ navigate }) {
  const [cart, setCart] = useCart();
  const [merchant] = useStore("merchant", null);
  const [receipt, setReceipt] = useState(null);
  const [method, setMethod] = useState("mobile");
  const [result, setResult] = useState("success");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const locked = useRef(false);
  const summary = totals(cart);
  async function pay() {
    if (locked.current) return;
    if (!merchant?.businessName || !merchant?.point) {
      navigate("/signup");
      return;
    }
    if (!summary.count) return;
    locked.current = true;
    setBusy(true);
    setError("");
    try {
      await new Promise((resolve) => setTimeout(resolve, 1100));
      if (result === "declined")
        throw new Error(
          "The simulated payment was declined. Your basket is saved; try again with a successful payment.",
        );
      const order = {
        id: "BG-" + crypto.randomUUID().slice(0, 8).toUpperCase(),
        createdAt: new Date().toISOString(),
        merchant,
        method,
        ...summary,
        status: "Demo payment successful",
      };
      write("last-order", order);
      setCart({});
      setReceipt(order);
    } catch (e) {
      setError(e.message || "Could not save your order. Please try again.");
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  function change(p, delta) {
    try {
      setCart({
        ...cart,
        [p.id]: Math.max(0, Math.min(p.stock, p.quantity + delta)),
      });
    } catch {
      setError("Could not update your basket. Check browser storage settings.");
    }
  }
  if (receipt)
    return (
      <div className="page">
        <div className="receipt card">
          <div className="success-icon">
            <Check size={33} />
          </div>
          <div className="eyebrow">ONE LESS THING ON YOUR TO-DO LIST</div>
          <h1>You’re all stocked up.</h1>
          <p className="muted">
            Your demo order has been placed, {receipt.merchant.owner}.
          </p>
          <span className="pill">{receipt.id}</span>
          <div className="receipt-details">
            <div className="row">
              <span>Order total</span>
              <strong>{money(receipt.total)}</strong>
            </div>
            <div className="row">
              <span>Items ordered</span>
              <strong>{receipt.count}</strong>
            </div>
            <div className="row">
              <span>Deliver to</span>
              <strong>{receipt.merchant.businessName}</strong>
            </div>
            <p className="muted">
              {receipt.merchant.address}, {receipt.merchant.city}
            </p>
          </div>
          <p className="notice">
            Payment and delivery are simulated. No money was charged and no
            delivery will be dispatched.
          </p>
          <button className="btn primary" onClick={() => navigate("/orders")}>
            Continue shopping <ArrowRight size={16} />
          </button>
        </div>
      </div>
    );
  if (!summary.count)
    return (
      <div className="page empty">
        <div className="success-icon">
          <ShoppingBag size={30} />
        </div>
        <h1>Your next restock is waiting.</h1>
        <p className="muted">
          Add a few essentials to your basket to get started.
        </p>
        <button className="btn primary" onClick={() => navigate("/orders")}>
          Browse inventory <ArrowRight size={16} />
        </button>
      </div>
    );
  return (
    <div className="page checkout-page">
      <button
        className="link-button back-link"
        onClick={() => navigate("/orders")}
      >
        <ArrowLeft size={15} /> Continue shopping
      </button>
      <div className="page-heading">
        <div>
          <div className="eyebrow">A FULLER SHELF IS A FEW CLICKS AWAY</div>
          <h1>Let’s make it an order.</h1>
          <p className="muted">
            Review your stock, confirm your doorstep, and you’re good to go.
          </p>
        </div>
        <span className="pill">
          <ShieldCheck size={14} /> Demo checkout
        </span>
      </div>
      <div className="checkout-layout">
        <div>
          <section className="card">
            <div className="row">
              <h2>Your order</h2>
              <span className="muted">{summary.count} items</span>
            </div>
            <div className="order-lines">
              {summary.items.map((p) => (
                <article className="order-line" key={p.id}>
                  <div className="line-art">
                    <ProductArt product={p} />
                  </div>
                  <div className="line-name">
                    <h3>{p.name}</h3>
                    <p>{p.unit}</p>
                    <span>{money(p.price)} each</span>
                  </div>
                  <div className="quantity">
                    <button
                      disabled={busy}
                      aria-label={"Decrease " + p.name}
                      onClick={() => change(p, -1)}
                    >
                      −
                    </button>
                    <span>{p.quantity}</span>
                    <button
                      disabled={busy || p.quantity >= p.stock}
                      aria-label={"Increase " + p.name}
                      onClick={() => change(p, 1)}
                    >
                      +
                    </button>
                  </div>
                  <strong>{money(p.price * p.quantity)}</strong>
                </article>
              ))}
            </div>
          </section>
          <section className="card delivery-card">
            <div className="row">
              <h2>
                <MapPin size={19} /> Delivery details
              </h2>
              <button
                className="link-button"
                disabled={busy}
                onClick={() => navigate("/signup")}
              >
                {merchant ? "Edit" : "Add business"}
              </button>
            </div>
            {merchant ? (
              <>
                <strong>{merchant.businessName}</strong>
                <p className="muted">
                  {merchant.address}, {merchant.city}
                  <br />
                  {merchant.owner} · {merchant.phone}
                </p>
                <div className="notice">
                  <Truck size={16} /> Estimated demo delivery: next business day
                </div>
              </>
            ) : (
              <p className="muted">
                Add your business name and delivery pin before placing your
                order.
              </p>
            )}
          </section>
          <section className="card payment-card">
            <h2>How would you like to pay?</h2>
            <p className="muted">
              Try the checkout experience with a simulated payment.
            </p>
            <div className="payment-methods">
              {[
                ["mobile", Smartphone, "M-Pesa", "Simulated mobile payment"],
                ["card", Wallet, "Card", "Simulated card payment"],
              ].map(([id, Icon, label, description]) => (
                <label
                  className={
                    method === id ? "payment-option selected" : "payment-option"
                  }
                  key={id}
                >
                  <input
                    type="radio"
                    name="payment"
                    value={id}
                    checked={method === id}
                    disabled={busy}
                    onChange={() => setMethod(id)}
                  />
                  <Icon size={22} />
                  <span>
                    <strong>{label}</strong>
                    <small>{description}</small>
                  </span>
                </label>
              ))}
            </div>
            <label className="field simulation-control">
              Demo payment outcome
              <select
                value={result}
                disabled={busy}
                onChange={(e) => setResult(e.target.value)}
              >
                <option value="success">Successful payment</option>
                <option value="declined">Declined payment</option>
              </select>
            </label>
            <p className="simulation-caption">
              No real payment details are collected.
            </p>
          </section>
        </div>
        <aside className="card summary-card">
          <h2>Order summary</h2>
          <div className="row">
            <span>Subtotal</span>
            <strong>{money(summary.subtotal)}</strong>
          </div>
          <div className="row">
            <span>Delivery</span>
            <strong>
              {summary.delivery ? money(summary.delivery) : "Free"}
            </strong>
          </div>
          <p className="delivery-threshold">
            Free delivery on orders of KES 15,000 or more.
          </p>
          <hr className="divider" />
          <div className="row grand-total">
            <span>Total</span>
            <strong>{money(summary.total)}</strong>
          </div>
          <p className="muted summary-hint">
            All prices are demo prices. No additional fees.
          </p>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button className="btn primary wide" disabled={busy} onClick={pay}>
            {busy
              ? "Simulating payment…"
              : merchant
                ? "Place demo order"
                : "Add delivery details"}
            {!busy && <ArrowRight size={16} />}
          </button>
          <p className="payment-disclaimer">
            <ShieldCheck size={14} /> This is a simulated transaction.
            <br />
            You won’t be charged.
          </p>
          <div role="status" className="sr-only">
            {busy ? "Payment is processing" : ""}
          </div>
        </aside>
      </div>
    </div>
  );
}
