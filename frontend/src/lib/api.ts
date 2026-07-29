const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Error de conexión");
  }
  return res.json();
}

export async function getProducts() {
  return fetchAPI<import("./types").ProductListItem[]>("/api/products");
}

export async function getProduct(id: string) {
  return fetchAPI<import("./types").Product>(`/api/products/${id}`);
}

export async function createCheckoutPreference(data: import("./types").CheckoutRequest) {
  return fetchAPI<import("./types").PreferenceResponse>("/api/checkout/create-preference", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getOrder(id: string) {
  return fetchAPI<import("./types").Order>(`/api/checkout/orders/${id}`);
}

export async function getOrders() {
  return fetchAPI<import("./types").Order[]>("/api/checkout/orders");
}

export async function getStats() {
  return fetchAPI<import("./types").StatsSummary>("/api/admin/stats");
}

export async function getTopProducts(limit = 10) {
  return fetchAPI<import("./types").TopProduct[]>(`/api/admin/top-products?limit=${limit}`);
}

export async function getSalesReport(days = 30) {
  return fetchAPI<import("./types").SalesReportRow[]>(`/api/admin/reports/sales?days=${days}`);
}

export async function getProfitReport() {
  return fetchAPI<import("./types").ProfitReport>("/api/admin/reports/profit");
}

export function getExportUrl(type: "orders" | "products" | "profit") {
  return `${API_BASE}/api/admin/export/${type}`;
}
