import React, { useEffect, useState } from "react";
import { api } from "./api";
import { money } from "./catalog.mjs";
export default function OrderHistory() {
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api("/orders", { signal: controller.signal })
      .then(setOrders)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, []);
  return (
    <section className="card" style={{ marginTop: 28 }}>
      <h2>Recent orders</h2>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!orders.length && !error && (
        <p className="muted">Your placed orders will appear here.</p>
      )}
      {orders.map((o) => (
        <div
          className="row"
          style={{
            padding: "12px 0",
            borderTop: "1px solid var(--border)",
            flexWrap: "wrap",
          }}
          key={o.id}
        >
          <div>
            <strong>BG-{o.id.slice(0, 8).toUpperCase()}</strong>
            <small className="muted" style={{ display: "block" }}>
              {new Date(o.createdAt).toLocaleString()}
            </small>
          </div>
          <span className="pill">{o.status}</span>
          <strong>{o.total !== undefined ? money(o.total) : "—"}</strong>
          {o.error && <small className="muted">{o.error}</small>}
        </div>
      ))}
    </section>
  );
}
