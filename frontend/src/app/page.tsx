import { getProducts } from "@/lib/api";
import ProductCard from "@/components/ProductCard";

export default async function HomePage() {
  let products;
  try {
    products = await getProducts();
  } catch {
    return (
      <div className="text-center py-20">
        <h1 className="text-2xl font-bold text-gray-900">DropStore</h1>
        <p className="text-gray-500 mt-2">No se pudieron cargar los productos. Asegúrate de que el backend esté corriendo.</p>
      </div>
    );
  }

  const categories = [...new Set(products.filter((p) => p.category).map((p) => p.category))];

  return (
    <div className="space-y-12">
      <section className="text-center py-8">
        <h1 className="text-4xl font-bold text-gray-900">Productos Destacados</h1>
        <p className="text-gray-500 mt-2">Encuentra los mejores productos con envío rápido a todo Perú</p>
      </section>

      {categories.length > 0 ? (
        categories.map((cat) => {
          const catProducts = products.filter((p) => p.category === cat);
          if (catProducts.length === 0) return null;
          return (
            <section key={cat}>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">{cat}</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {catProducts.map((p) => (
                  <ProductCard
                    key={p.id}
                    id={p.id}
                    name={p.name}
                    image={p.images?.[0] || ""}
                    price={p.selling_price}
                    category={p.category}
                    stock={p.stock}
                  />
                ))}
              </div>
            </section>
          );
        })
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {products.map((p) => (
            <ProductCard
              key={p.id}
              id={p.id}
              name={p.name}
              image={p.images?.[0] || ""}
              price={p.selling_price}
              category={p.category}
              stock={p.stock}
            />
          ))}
        </div>
      )}
    </div>
  );
}
