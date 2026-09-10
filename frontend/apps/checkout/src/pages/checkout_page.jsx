import React, { useEffect, useRef, useState } from "react";
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
import { useCart, useStore, write, read } from "../../../../shared/store";
import { totals, money } from "../../../../shared/catalog.mjs";
import ProductArt from "../../../../shared/ProductArt";
import "../styles/checkout_page.css";
import { api, useCatalog } from "../../../../shared/api";
export default function Checkout({ navigate }) {
  const {
    products,
    loading: catalogLoading,
    error: catalogError,
    refresh,
  } = useCatalog();
  const [quote, setQuote] = useState(null);
  const [quoteError, setQuoteError] = useState("");
  const [quoting, setQuoting] = useState(false);
  const [attempt, setAttempt] = useState(() => read("order-attempt", null));
  const [cart, setCart] = useCart();
  const [merchant] = useStore("merchant", null);
  const [receipt, setReceipt] = useState(null);
  const [method, setMethod] = useState("mobile");
  const [result, setResult] = useState("success");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const locked = useRef(false);
  const summary = quote || totals(cart, products);
  const basketKey = JSON.stringify(cart);
  useEffect(() => {
    const controller = new AbortController();
    setQuote(null);
    setQuoteError("");
    if (!Object.keys(cart).length) return;
    setQuoting(true);
    api("/catalog/quote", {
      method: "POST",
      body: {
        items: Object.entries(cart).map(([id, quantity]) => ({ id, quantity })),
      },
      signal: controller.signal,
    })
      .then(setQuote)
      .catch((e) => {
        if (!controller.signal.aborted) setQuoteError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setQuoting(false);
      });
    return () => controller.abort();
  }, [basketKey, products]);
  async function pay() {
    if (locked.current) return;
    if (!merchant?.id || !read("session", null)) {
      navigate("/signup");
      return;
    }
    if (!attempt && (!quote || quoting)) return;
    locked.current = true;
    setBusy(true);
    setError("");
    try {
      let current = attempt;
      if (current && current.merchantId !== merchant.id)
        throw new Error(
          "The pending order belongs to another business session.",
        );
      if (!current) {
        current = {
          key: crypto.randomUUID(),
          merchantId: merchant.id,
          payload: {
            items: Object.entries(cart).map(([id, quantity]) => ({
              id,
              quantity,
            })),
            expected_total: quote.total,
            method,
            outcome: result,
          },
        };
        write("order-attempt", current);
        setAttempt(current);
      }
      let order = await api("/orders", {
        method: "POST",
        body: current.payload,
        headers: { "Idempotency-Key": current.key },
      });
      for (let i = 0; order.status === "pending" && i < 8; i++) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        order = await api("/orders/" + order.id);
      }
      if (order.status === "pending") {
        setError(
          "Your order is still processing. Use Check order status to safely resume it.",
        );
        return;
      }
      write("order-attempt", null);
      setAttempt(null);
      if (order.status !== "confirmed") {
        refresh();
        throw new Error(order.error || "The order could not be completed.");
      }
      setReceipt(order);
      write("last-order", order);
      setCart({});
      refresh();
    } catch (e) {
      if ([400, 401, 422].includes(e.status)) {
        write("order-attempt", null);
        setAttempt(null);
      }
      setError(
        e.message ||
          "Could not place the order. Retry to safely resume the same request.",
      );
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
            Your order has been saved, {receipt.merchant.owner}.
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
  if (!summary.count && !attempt)
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
              {Object.keys(cart)
                .filter((id) => !products.some((p) => p.id === id))
                .map((id) => (
                  <div className="row" key={id}>
                    <span>Unavailable product: {id}</span>
                    <button
                      className="link-button"
                      disabled={busy || !!attempt}
                      onClick={() =>
                        setCart(
                          Object.fromEntries(
                            Object.entries(cart).filter(([key]) => key !== id),
                          ),
                        )
                      }
                    >
                      Remove
                    </button>
                  </div>
                ))}
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
                      disabled={busy || !!attempt}
                      aria-label={"Decrease " + p.name}
                      onClick={() => change(p, -1)}
                    >
                      −
                    </button>
                    <span>{p.quantity}</span>
                    <button
                      disabled={busy || !!attempt || p.quantity >= p.stock}
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
                disabled={busy || !!attempt}
                onClick={() => navigate("/signup")}
              >
                {merchant?.id ? "Edit" : "Add business"}
              </button>
            </div>
            {merchant?.id ? (
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
                    disabled={busy || !!attempt}
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
                disabled={busy || !!attempt}
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
          {(catalogLoading || quoting) && (
            <p role="status" className="muted">
              Checking current prices and stock…
            </p>
          )}
          {(quoteError || catalogError) && (
            <p role="alert" className="error">
              {quoteError || catalogError}{" "}
              <button className="link-button" onClick={refresh}>
                Refresh
              </button>
            </p>
          )}
          {attempt && (
            <p className="notice">
              An order request is in progress. Check its status before placing
              another order.
            </p>
          )}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button
            className="btn primary wide"
            disabled={
              busy ||
              (!attempt &&
                (quoting || !quote || !!quoteError || !!catalogError))
            }
            onClick={pay}
          >
            {busy
              ? "Placing order…"
              : attempt
                ? "Check order status"
                : merchant?.id
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
