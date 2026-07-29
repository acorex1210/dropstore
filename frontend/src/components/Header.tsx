"use client";
import Link from "next/link";
import { useCart } from "@/context/CartContext";

export default function Header() {
  const { count } = useCart();

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-primary-700">
          DropStore
        </Link>
        <nav className="flex items-center gap-6">
          <Link href="/" className="text-sm text-gray-700 hover:text-primary-600">
            Productos
          </Link>
          <Link href="/checkout" className="relative text-sm text-gray-700 hover:text-primary-600">
            Carrito
            {count > 0 && (
              <span className="absolute -top-2 -right-4 bg-primary-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {count}
              </span>
            )}
          </Link>
          <Link href="/admin" className="text-sm text-gray-700 hover:text-primary-600">
            Admin
          </Link>
        </nav>
      </div>
    </header>
  );
}
