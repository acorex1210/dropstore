"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getOrder } from "@/lib/api";
import type { Order } from "@/lib/types";

export default function SuccessPage() {
  const searchParams = useSearchParams();
  const [order, setOrder] = useState<Order | null>(null);

  useEffect(() => {
    const paymentId = searchParams.get("payment_id");
    const externalRef = searchParams.get("external_reference");
    if (externalRef) {
      getOrder(externalRef).then(setOrder).catch(() => {});
    }
  }, [searchParams]);

  return (
    <div className="text-center py-20 max-w-lg mx-auto">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <span className="text-3xl text-green-600">✓</span>
      </div>
      <h1 className="text-3xl font-bold text-gray-900">¡Pago exitoso!</h1>
      <p className="text-gray-500 mt-2">Tu pedido ha sido registrado. Te enviaremos el número de seguimiento cuando sea despachado.</p>

      {order && (
        <div className="mt-6 bg-white border border-gray-200 rounded-xl p-4 text-left text-sm space-y-2">
          <p><span className="text-gray-500">Orden:</span> <span className="font-medium">{order.id.slice(0, 8)}...</span></p>
          <p><span className="text-gray-500">Total:</span> <span className="font-medium">S/ {order.total_amount.toFixed(2)}</span></p>
          <p><span className="text-gray-500">Estado:</span> <span className="text-green-600 font-medium">{order.status}</span></p>
        </div>
      )}

      <Link href="/" className="inline-block mt-8 text-primary-600 hover:underline font-medium">
        Seguir comprando
      </Link>
    </div>
  );
}
