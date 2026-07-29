"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getProduct } from "@/lib/api";
import { useCart } from "@/context/CartContext";
import type { Product } from "@/lib/types";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { addItem } = useCart();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);

  useEffect(() => {
    if (!id) return;
    getProduct(id)
      .then(setProduct)
      .catch(() => router.push("/"))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return <div className="text-center py-20 text-gray-500">Cargando...</div>;
  if (!product) return null;

  function handleAdd() {
    addItem({
      product_id: product.id,
      product_name: product.name,
      product_image: product.images?.[0] || "",
      selling_price: product.selling_price,
      quantity: qty,
    });
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  }

  const marginAmount = product.selling_price - product.base_price;

  return (
    <div className="grid md:grid-cols-2 gap-8">
      <div className="aspect-square bg-gray-100 rounded-xl overflow-hidden">
        <img
          src={product.images?.[0] || "https://picsum.photos/seed/placeholder/600/600"}
          alt={product.name}
          className="w-full h-full object-cover"
        />
      </div>

      <div className="space-y-6">
        <div>
          {product.category && (
            <span className="text-xs text-gray-500 uppercase tracking-wide">{product.category}</span>
          )}
          <h1 className="text-3xl font-bold text-gray-900 mt-1">{product.name}</h1>
        </div>

        <div>
          <span className="text-4xl font-bold text-primary-700">
            S/ {product.selling_price.toFixed(2)}
          </span>
          <div className="text-sm text-gray-500 mt-1">
            Costo: S/ {product.base_price.toFixed(2)} | Margen: S/ {marginAmount.toFixed(2)} ({product.margin_percentage}%)
          </div>
        </div>

        {product.description && (
          <p className="text-gray-600 leading-relaxed">{product.description}</p>
        )}

        <div className="flex items-center gap-4">
          <div className="flex items-center border border-gray-300 rounded-lg">
            <button
              onClick={() => setQty(Math.max(1, qty - 1))}
              className="px-3 py-2 text-gray-600 hover:bg-gray-100"
            >
              -
            </button>
            <span className="px-4 py-2 font-medium">{qty}</span>
            <button
              onClick={() => setQty(Math.min(product.stock, qty + 1))}
              className="px-3 py-2 text-gray-600 hover:bg-gray-100"
            >
              +
            </button>
          </div>

          {product.stock > 0 ? (
            <span className="text-sm text-gray-500">{product.stock} unidades disponibles</span>
          ) : (
            <span className="text-sm text-red-500">Agotado</span>
          )}
        </div>

        <button
          onClick={handleAdd}
          disabled={product.stock === 0}
          className={`w-full py-3 rounded-lg font-semibold transition-colors ${
            added
              ? "bg-green-100 text-green-800"
              : "bg-primary-600 text-white hover:bg-primary-700 disabled:bg-gray-300"
          }`}
        >
          {added ? "✓ Agregado al carrito" : "Agregar al carrito"}
        </button>

        {product.variants && product.variants.length > 0 && (
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Variantes</h3>
            <div className="flex flex-wrap gap-2">
              {product.variants.map((v) => (
                <span key={v.id} className="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-700">
                  {v.name}{v.selling_price ? ` - S/ ${v.selling_price.toFixed(2)}` : ""}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
