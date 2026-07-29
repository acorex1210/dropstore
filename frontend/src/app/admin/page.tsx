"use client";
import { useEffect, useState } from "react";
import { getOrders, getStats, getProfitReport, getExportUrl } from "@/lib/api";
import type { Order, StatsSummary, ProfitReport } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Tab = "dashboard" | "profit" | "export";

const tabs: { key: Tab; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "profit", label: "Rentabilidad" },
  { key: "export", label: "Exportar" },
];

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [profit, setProfit] = useState<ProfitReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [dispatchOrder, setDispatchOrder] = useState<Order | null>(null);
  const [dropiId, setDropiId] = useState("");
  const [tracking, setTracking] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    Promise.all([
      getOrders().then(setOrders).catch(() => {}),
      getStats().then(setStats).catch(() => {}),
      getProfitReport().then(setProfit).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const statusColors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    paid: "bg-green-100 text-green-800",
    processing: "bg-blue-100 text-blue-800",
    shipped: "bg-purple-100 text-purple-800",
    delivered: "bg-gray-100 text-gray-800",
    cancelled: "bg-red-100 text-red-800",
  };

  const paidOrders = orders.filter((o) => o.status === "paid");
  const recentOrders = orders.slice(0, 10);

  async function handleDispatch(e: React.FormEvent) {
    e.preventDefault();
    if (!dispatchOrder || !dropiId) return;
    setMsg("");
    try {
      const res = await fetch(`${API_BASE}/api/checkout/dispatch/${dispatchOrder.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider_order_id: dropiId,
          tracking_number: tracking || null,
          tracking_url: tracking ? `https://www.dropi.co/tracking/${tracking}` : null,
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error");
      setMsg("✓ Orden despachada correctamente");
      setDropiId("");
      setTracking("");
      setDispatchOrder(null);
      const updated = await getOrders();
      setOrders(updated);
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    }
  }

  if (loading) return <div className="text-center py-20 text-gray-500">Cargando...</div>;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-gray-900">Panel de Administración</h1>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Dashboard Tab ── */}
      {tab === "dashboard" && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-gray-900">{stats?.total_orders ?? orders.length}</p>
              <p className="text-sm text-gray-500">Total pedidos</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-amber-600">{stats?.paid_pending ?? paidOrders.length}</p>
              <p className="text-sm text-gray-500">Pendientes de envío</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-blue-600">{stats ? (stats.processing + stats.shipped) : orders.filter((o) => ["processing", "shipped", "delivered"].includes(o.status)).length}</p>
              <p className="text-sm text-gray-500">En proceso</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-green-600">S/ {(stats?.total_margin ?? 0).toFixed(2)}</p>
              <p className="text-sm text-gray-500">Margen total</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-gray-900">S/ {(stats?.total_revenue ?? 0).toFixed(2)}</p>
              <p className="text-sm text-gray-500">Ingresos totales</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-red-600">S/ {(stats?.total_cost ?? 0).toFixed(2)}</p>
              <p className="text-sm text-gray-500">Costo total</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-indigo-600">{stats?.avg_margin_pct ?? 0}%</p>
              <p className="text-sm text-gray-500">Margen promedio</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-teal-600">S/ {(stats?.today_revenue ?? 0).toFixed(2)}</p>
              <p className="text-sm text-gray-500">Hoy ({stats?.today_orders ?? 0} pedidos)</p>
            </div>
          </div>

          {/* Dispatch Queue */}
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Órdenes por despachar a Dropi
              {paidOrders.length > 0 && (
                <span className="ml-2 text-sm font-normal text-gray-500">({paidOrders.length} pendientes)</span>
              )}
            </h2>
            {paidOrders.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
                No hay órdenes pendientes de envío
              </div>
            ) : (
              <div className="space-y-4">
                {paidOrders.map((order) => (
                  <div key={order.id} className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-mono text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
                            {order.id.slice(0, 8)}
                          </span>
                          <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[order.status]}`}>
                            {order.status}
                          </span>
                          <span className="text-sm text-gray-500">
                            {new Date(order.created_at).toLocaleString("es-PE")}
                          </span>
                        </div>
                        <div className="grid md:grid-cols-3 gap-4 text-sm">
                          <div>
                            <p className="text-gray-900 font-medium">S/ {order.total_amount.toFixed(2)}</p>
                            <p className="text-gray-500">Margen: S/ {order.total_margin.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-gray-700">{order.shipping_address}</p>
                            <p className="text-gray-500">{order.shipping_city}, {order.shipping_department}</p>
                          </div>
                          <div>
                            <p className="text-primary-600 font-medium">
                              {order.items.map((i) => i.product_name).join(", ")}
                            </p>
                            <p className="text-gray-500">{order.items.length} producto(s)</p>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => { setDispatchOrder(order); setDropiId(""); setTracking(""); setMsg(""); }}
                        className="shrink-0 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700"
                      >
                        Despachar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Recent orders table */}
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Órdenes recientes</h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="text-left px-4 py-3 font-medium">Orden</th>
                      <th className="text-left px-4 py-3 font-medium">Cliente</th>
                      <th className="text-right px-4 py-3 font-medium">Total</th>
                      <th className="text-right px-4 py-3 font-medium">Margen</th>
                      <th className="text-center px-4 py-3 font-medium">Estado</th>
                      <th className="text-center px-4 py-3 font-medium">Dropi ID</th>
                      <th className="text-left px-4 py-3 font-medium">Tracking</th>
                      <th className="text-left px-4 py-3 font-medium">Fecha</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {recentOrders.map((order) => (
                      <tr key={order.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-mono text-xs text-gray-500">{order.id.slice(0, 8)}...</td>
                        <td className="px-4 py-3 text-gray-900">{order.shipping_city}</td>
                        <td className="px-4 py-3 text-right font-medium">S/ {order.total_amount.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right text-green-600 font-medium">S/ {order.total_margin.toFixed(2)}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${statusColors[order.status] || "bg-gray-100"}`}>
                            {order.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 font-mono text-center">
                          {order.provider_order_id ? order.provider_order_id.slice(0, 8) + "..." : "-"}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">{order.tracking_number || "-"}</td>
                        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                          {new Date(order.created_at).toLocaleDateString("es-PE")}
                        </td>
                      </tr>
                    ))}
                    {recentOrders.length === 0 && (
                      <tr><td colSpan={8} className="text-center py-8 text-gray-500">No hay pedidos aún</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </>
      )}

      {/* ── Profit Analytics Tab ── */}
      {tab === "profit" && profit && (
        <div className="space-y-8">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-gray-900">S/ {profit.totals.revenue.toFixed(2)}</p>
              <p className="text-sm text-gray-500">Ingresos totales</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-red-600">S/ {profit.totals.cost.toFixed(2)}</p>
              <p className="text-sm text-gray-500">Costo total</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-green-600">S/ {profit.totals.margin.toFixed(2)}</p>
              <p className="text-sm text-gray-500">Margen total</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-indigo-600">{profit.totals.margin_pct}%</p>
              <p className="text-sm text-gray-500">Margen promedio</p>
            </div>
          </div>

          {/* Products table */}
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Rentabilidad por producto</h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="text-left px-4 py-3 font-medium">Producto</th>
                      <th className="text-right px-4 py-3 font-medium">Unidades</th>
                      <th className="text-right px-4 py-3 font-medium">Ingreso</th>
                      <th className="text-right px-4 py-3 font-medium">Costo</th>
                      <th className="text-right px-4 py-3 font-medium">Margen</th>
                      <th className="text-right px-4 py-3 font-medium">%</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {profit.products.map((p, i) => (
                      <tr key={p.product_id || i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-900">{p.product_name}</td>
                        <td className="px-4 py-3 text-right">{p.units_sold}</td>
                        <td className="px-4 py-3 text-right">S/ {p.revenue.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right text-red-600">S/ {p.cost.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right text-green-600 font-medium">S/ {p.margin.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right font-medium">{p.margin_pct}%</td>
                      </tr>
                    ))}
                    {profit.products.length === 0 && (
                      <tr><td colSpan={6} className="text-center py-8 text-gray-500">Sin datos</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          {/* By month */}
          <section>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Rentabilidad por mes</h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="text-left px-4 py-3 font-medium">Mes</th>
                      <th className="text-right px-4 py-3 font-medium">Pedidos</th>
                      <th className="text-right px-4 py-3 font-medium">Ingreso</th>
                      <th className="text-right px-4 py-3 font-medium">Costo</th>
                      <th className="text-right px-4 py-3 font-medium">Margen</th>
                      <th className="text-right px-4 py-3 font-medium">%</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {profit.months.map((m) => (
                      <tr key={m.year_month} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-900">{m.year_month}</td>
                        <td className="px-4 py-3 text-right">{m.orders}</td>
                        <td className="px-4 py-3 text-right">S/ {m.revenue.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right text-red-600">S/ {m.cost.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right text-green-600 font-medium">S/ {m.margin.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right font-medium">{m.margin_pct}%</td>
                      </tr>
                    ))}
                    {profit.months.length === 0 && (
                      <tr><td colSpan={6} className="text-center py-8 text-gray-500">Sin datos</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ── Export Tab ── */}
      {tab === "export" && (
        <div className="max-w-lg space-y-6">
          <p className="text-gray-600">Descarga los datos en formato CSV para analizar en Excel / Google Sheets.</p>

          <a
            href={getExportUrl("orders")}
            className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-primary-300 hover:shadow-sm transition-all"
          >
            <h3 className="font-bold text-gray-900">📦 Exportar pedidos</h3>
            <p className="text-sm text-gray-500 mt-1">Todas las órdenes con items, tracking, montos</p>
          </a>

          <a
            href={getExportUrl("products")}
            className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-primary-300 hover:shadow-sm transition-all"
          >
            <h3 className="font-bold text-gray-900">🏷️ Exportar productos</h3>
            <p className="text-sm text-gray-500 mt-1">Catálogo completo con precios, márgenes, variantes</p>
          </a>

          <a
            href={getExportUrl("profit")}
            className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-primary-300 hover:shadow-sm transition-all"
          >
            <h3 className="font-bold text-gray-900">📊 Exportar rentabilidad</h3>
            <p className="text-sm text-gray-500 mt-1">Detalle de cada item vendido: precio, costo, margen</p>
          </a>
        </div>
      )}

      {/* Dispatch Modal */}
      {dispatchOrder && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">Despachar orden a Dropi</h3>
              <button onClick={() => setDispatchOrder(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>
            <div className="bg-gray-50 rounded-xl p-4 space-y-2 text-sm font-mono">
              <p className="font-semibold text-gray-700 text-xs uppercase tracking-wide">Datos para ingresar en Dropi</p>
              <div className="space-y-1 text-gray-800">
                <p><span className="text-gray-500">Cliente:</span> {dispatchOrder.shipping_address}</p>
                <p><span className="text-gray-500">Ciudad:</span> {dispatchOrder.shipping_city?.toUpperCase()}</p>
                <p><span className="text-gray-500">Departamento:</span> {dispatchOrder.shipping_department?.toUpperCase()}</p>
                <p><span className="text-gray-500">Dirección:</span> {dispatchOrder.shipping_address}</p>
                <hr className="border-gray-200 my-2" />
                <p className="text-gray-500 font-semibold">Productos:</p>
                {dispatchOrder.items.map((item, i) => (
                  <p key={i}>{i + 1}. {item.product_name}{item.variant_name ? ` (${item.variant_name})` : ""} x{item.quantity} — S/ {item.unit_price.toFixed(2)} c/u</p>
                ))}
                <hr className="border-gray-200 my-2" />
                <p><span className="text-gray-500">Total:</span> <span className="font-bold">S/ {dispatchOrder.total_amount.toFixed(2)}</span></p>
                <p><span className="text-gray-500">Tipo de pago:</span> SIN RECAUDO (ya pagó con Mercado Pago)</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Ingresa estos datos en{" "}
              <a href="https://dropi.pe" target="_blank" className="text-primary-600 hover:underline" rel="noreferrer">dropi.pe</a>{" "}
              → Orden Manual. Después de crear la orden, pega los datos aquí:
            </p>
            <form onSubmit={handleDispatch} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ID de la orden en Dropi <span className="text-red-500">*</span>
                </label>
                <input value={dropiId} onChange={(e) => setDropiId(e.target.value)} required
                  placeholder="Ej: 12345"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Número de guía / tracking (opcional)</label>
                <input value={tracking} onChange={(e) => setTracking(e.target.value)}
                  placeholder="Lo puedes agregar después"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none" />
              </div>
              {msg && <p className={`text-sm ${msg.startsWith("✓") ? "text-green-600" : "text-red-600"}`}>{msg}</p>}
              <div className="flex gap-3">
                <button type="submit" className="flex-1 bg-primary-600 text-white py-2 rounded-lg font-medium hover:bg-primary-700">
                  Confirmar despacho
                </button>
                <button type="button" onClick={() => setDispatchOrder(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
