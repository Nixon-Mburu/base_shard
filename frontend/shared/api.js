import { useCallback, useEffect, useState } from "react";
import { read, write } from "./store";
export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}
export async function api(
  path,
  { method = "GET", body, headers = {}, signal } = {},
) {
  const token = read("session", null);
  const timeout = AbortSignal.timeout(15000);
  let response;
  try {
    response = await fetch("/api" + path, {
      method,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: "Bearer " + token } : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new ApiError("The service could not be reached. Please try again.");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      "The API returned an unexpected response. Check that the backend is running.",
      response.status,
    );
  }
  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((e) => e.msg).join("; ")
          : "Request failed";
    throw new ApiError(detail, response.status);
  }
  return data;
}
export function useCatalog() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    api("/catalog/products", { signal: controller.signal })
      .then((data) => {
        setProducts(data);
        setError("");
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [version]);
  useEffect(() => {
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [refresh]);
  return { products, loading, error, refresh };
}
export async function saveMerchant(profile) {
  const token = read("session", null);
  if (token) {
    const merchant = await api("/merchants/me", {
      method: "PUT",
      body: profile,
    });
    write("merchant", merchant);
    return merchant;
  }
  const data = await api("/merchants", { method: "POST", body: profile });
  write("session", data.token);
  write("merchant", data.merchant);
  return data.merchant;
}
