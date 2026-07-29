import Link from "next/link";

interface Props {
  id: string;
  name: string;
  image: string;
  price: number;
  category: string | null;
  stock: number;
}

export default function ProductCard({ id, name, image, price, category, stock }: Props) {
  return (
    <Link href={`/products/${id}`} className="group block bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
      <div className="aspect-square bg-gray-50 overflow-hidden">
        <img
          src={image}
          alt={name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
        />
      </div>
      <div className="p-4 space-y-2">
        {category && (
          <span className="text-xs text-gray-500 uppercase tracking-wide">{category}</span>
        )}
        <h3 className="font-semibold text-gray-900 leading-tight">{name}</h3>
        <div className="flex items-center justify-between">
          <span className="text-lg font-bold text-primary-700">
            S/ {price.toFixed(2)}
          </span>
          {stock <= 5 && stock > 0 && (
            <span className="text-xs text-amber-600">Últimos {stock}</span>
          )}
          {stock === 0 && (
            <span className="text-xs text-red-500">Agotado</span>
          )}
        </div>
      </div>
    </Link>
  );
}
