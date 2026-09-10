import React, { useEffect, useRef, useState } from "react";
import {
  Boxes,
  ShoppingBag,
  Store,
  CreditCard,
  ArrowUpRight,
  MapPin,
  Menu,
  PackageCheck,
} from "lucide-react";
import { useCart, useStore } from "../../../../shared/store";
import { cartCount } from "../../../../shared/catalog.mjs";
import "../styles/shell_page.css";
const routes = {
  "/orders": { app: "orders", label: "Order inventory" },
  "/signup": { app: "signup", label: "Your business" },
  "/checkout": { app: "checkout", label: "Checkout" },
};
export default function Shell() {
  const [path, setPath] = useState(location.pathname);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  const host = useRef();
  const [cart] = useCart();
  const [merchant] = useStore("merchant", null);
  const [open, setOpen] = useState(false);
  const route = routes[path];
  function navigate(to) {
    history.pushState({}, "", to);
    setPath(to);
    setOpen(false);
    window.scrollTo(0, 0);
  }
  useEffect(() => {
    if (location.pathname === "/") {
      history.replaceState({}, "", "/orders");
      setPath("/orders");
    }
    const pop = () => setPath(location.pathname);
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  useEffect(() => {
    if (!route) return;
    let cancelled = false,
      unmount;
    setLoading(true);
    setError("");
    const base = "/mfe/" + route.app;
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = base + "/assets/style.css";
    if (!import.meta.env.DEV) document.head.appendChild(css);
    const url =
      base + (import.meta.env.DEV ? "/src/remote.jsx" : "/assets/remote.js");
    import(/* @vite-ignore */ url)
      .then((module) => {
        if (!cancelled) {
          unmount = module.mount(host.current, { navigate });
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("This page could not load. Please try again.");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
      unmount?.();
      css.remove();
    };
  }, [route, retry]);
  return (
    <div className="shell">
      <aside className={"sidebar " + (open ? "is-open" : "")}>
        <a
          className="brand"
          href="/orders"
          onClick={(e) => {
            e.preventDefault();
            navigate("/orders");
          }}
        >
          <span className="brand-icon">
            <Boxes size={24} />
          </span>
          base<span className="brand-grid">grid</span>
          <span className="brand-dot">.</span>
        </a>
        <div className="workspace">
          <span className="workspace-icon">
            <Store size={19} />
          </span>
          <div>
            <strong>{merchant?.businessName || "Your business"}</strong>
            <small>Merchant workspace</small>
          </div>
          <span className="workspace-dot" />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {[
            ["/orders", ShoppingBag, "Order inventory"],
            ["/signup", Store, "Your business"],
            ["/checkout", CreditCard, "Checkout"],
          ].map(([url, Icon, label]) => (
            <a
              key={url}
              className={path === url ? "active" : ""}
              href={url}
              onClick={(e) => {
                e.preventDefault();
                navigate(url);
              }}
            >
              <Icon size={19} />
              {label}
              {url === "/checkout" && cartCount(cart) > 0 && (
                <span className="nav-count">{cartCount(cart)}</span>
              )}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="delivery-note">
            <PackageCheck size={25} />
            <h3>Your shelves, sorted.</h3>
            <p>
              Everyday essentials.
              <br />
              Delivered to your doorstep.
            </p>
            <button onClick={() => navigate("/orders")} className="link-button">
              Stock up today <ArrowUpRight size={14} />
            </button>
          </div>
          <div className="sidebar-footer">
            <span className="avatar">
              {merchant?.businessName?.[0]?.toUpperCase() || "M"}
            </span>
            <div>
              <strong>{merchant?.businessName || "Merchant account"}</strong>
              <small>
                {merchant ? "Business profile saved" : "Let’s get you set up"}
              </small>
            </div>
          </div>
        </div>
      </aside>
      <div className="shell-main">
        <header className="topbar">
          <button
            className="mobile-menu btn small"
            aria-label="Toggle navigation"
            onClick={() => setOpen(!open)}
          >
            <Menu size={19} />
          </button>
          <span className="breadcrumb">
            Workspace <span>/</span>{" "}
            <strong>{route?.label || "Page not found"}</strong>
          </span>
          <div className="topbar-right">
            <span className="delivery-location">
              <MapPin size={15} />
              {merchant?.city || "Delivering across Nairobi"}
            </span>
            <button
              className="header-cart"
              onClick={() => navigate("/checkout")}
              aria-label={"Cart, " + cartCount(cart) + " items"}
            >
              <ShoppingBag size={19} />
              <span>{cartCount(cart)}</span>
            </button>
            <span className="avatar small-avatar">
              {merchant?.businessName?.[0]?.toUpperCase() || "M"}
            </span>
          </div>
        </header>
        <main>
          {loading && route && (
            <div className="page muted" role="status">
              Getting your workspace ready…
            </div>
          )}
          {error && (
            <div className="page">
              <p role="alert">{error}</p>
              <button
                className="btn primary"
                onClick={() => setRetry(retry + 1)}
              >
                Try again
              </button>
            </div>
          )}
          {!route && path !== "/" && (
            <div className="empty">
              <h1>Page not found</h1>
              <button
                className="btn primary"
                onClick={() => navigate("/orders")}
              >
                Browse inventory
              </button>
            </div>
          )}
          <div ref={host} />
        </main>
        <footer className="main-footer">
          <span>© {new Date().getFullYear()} Base Grid</span>
          <span>Built for the businesses that keep us going.</span>
          <span>
            Made for merchants <span className="purple-dot">●</span>
          </span>
        </footer>
      </div>
    </div>
  );
}
