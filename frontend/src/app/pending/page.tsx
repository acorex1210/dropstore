import Link from "next/link";

export default function PendingPage() {
  return (
    <div className="text-center py-20 max-w-lg mx-auto">
      <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <span className="text-3xl text-amber-600">⏳</span>
      </div>
      <h1 className="text-3xl font-bold text-gray-900">Pago pendiente</h1>
      <p className="text-gray-500 mt-2">No hemos recibido la confirmación del pago aún. Si ya realizaste el pago, espera unos minutos.</p>
      <Link href="/" className="inline-block mt-8 text-primary-600 hover:underline font-medium">
        Volver a la tienda
      </Link>
    </div>
  );
}
