import documents from "./graphql.json";
import { useCallback, useEffect, useState } from "react";
import { read, write } from "./store";
export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}
export async function api(operation, { variables = {}, signal } = {}) {
  const token = read("session", null);
  const timeout = AbortSignal.timeout(15000);
  let response;
  try {
    response = await fetch("/graphql", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
      body: JSON.stringify({ query: documents[operation], variables }),
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError("The service could not be reached. Please try again.");
  }
  let result;
  try { result = await response.json(); }
  catch { throw new ApiError("The API returned an unexpected response", response.status); }
  if (!response.ok || result.errors?.length) {
    const error = result.errors?.[0];
    throw new ApiError(error?.message || "Request failed", error?.extensions?.status || response.status);
  }
  return result.data[operation];
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
    api("products", { signal: controller.signal })
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
    const merchant = await api("updateMerchant", {
      variables: { input: profile },
    });
    write("merchant", merchant);
    return merchant;
  }
  const data = await api("createMerchant", { variables: { input: profile } });
  write("session", data.token);
  write("merchant", data.merchant);
  return data.merchant;
}
