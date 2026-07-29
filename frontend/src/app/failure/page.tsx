import Link from "next/link";

export default function FailurePage() {
  return (
    <div className="text-center py-20 max-w-lg mx-auto">
      <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <span className="text-3xl text-red-500">✕</span>
      </div>
      <h1 className="text-3xl font-bold text-gray-900">Pago no completado</h1>
      <p className="text-gray-500 mt-2">El pago no pudo ser procesado. Puedes intentarlo de nuevo cuando quieras.</p>
      <Link href="/checkout" className="inline-block mt-8 text-primary-600 hover:underline font-medium">
        Reintentar pago
      </Link>
    </div>
  );
}
