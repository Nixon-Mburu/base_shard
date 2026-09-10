import React from "react";
import { createRoot } from "react-dom/client";
import Page from "./pages/checkout_page.jsx";
import "../../../shared/styles.css";
export function mount(
  element,
  { navigate = (path) => window.location.assign(path) } = {},
) {
  const root = createRoot(element);
  root.render(<Page navigate={navigate} />);
  return () => root.unmount();
}
