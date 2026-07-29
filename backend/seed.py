import asyncio

from app.database import async_session, create_tables
from app.models.product import Product
from app.services.margin import calc_selling_price

PRODUCTS = [
    {
        "name": "Auriculares Bluetooth Inalámbricos",
        "description": "Auriculares over-ear con cancelación de ruido activa, 30h de batería y sonido HD. Compatibles con todos los dispositivos Bluetooth.",
        "category": "Electrónicos",
        "images": ["https://picsum.photos/seed/headphones1/600/600"],
        "base_price": 45.00,
        "margin_percentage": 35,
        "stock": 50,
    },
    {
        "name": "Reloj Inteligente Deportivo",
        "description": "Smartwatch con monitor de frecuencia cardíaca, podómetro, GPS y resistencia al agua IP68. Ideal para hacer deporte.",
        "category": "Electrónicos",
        "images": ["https://picsum.photos/seed/watch1/600/600"],
        "base_price": 62.00,
        "margin_percentage": 30,
        "stock": 30,
    },
    {
        "name": "Mochila Impermeable para Laptop 15.6\"",
        "description": "Mochila ligera y resistente al agua con compartimento acolchado para laptop de hasta 15.6 pulgadas. Ideal para viajes y trabajo.",
        "category": "Accesorios",
        "images": ["https://picsum.photos/seed/backpack1/600/600"],
        "base_price": 28.50,
        "margin_percentage": 40,
        "stock": 80,
    },
    {
        "name": "Lámpara LED Escritorio con Brazo Flexible",
        "description": "Lámpara LED regulable con 3 temperaturas de color, brazo flexible y base con clip. Ideal para estudio y trabajo nocturno.",
        "category": "Hogar",
        "images": ["https://picsum.photos/seed/lamp1/600/600"],
        "base_price": 22.00,
        "margin_percentage": 35,
        "stock": 60,
    },
    {
        "name": "Kit de Maquillaje Profesional 48 colores",
        "description": "Paleta de sombras de 48 colores con alta pigmentación. Incluye espejo y brochas. Ideal para maquillaje profesional y diario.",
        "category": "Belleza",
        "images": ["https://picsum.photos/seed/makeup1/600/600"],
        "base_price": 18.00,
        "margin_percentage": 45,
        "stock": 100,
    },
    {
        "name": "Organizador de Cable USB 6 en 1",
        "description": "Cable multifunción con 6 puntas intercambiables (USB-C, Micro USB, Lightning). Carga y sincroniza todos tus dispositivos.",
        "category": "Electrónicos",
        "images": ["https://picsum.photos/seed/cable1/600/600"],
        "base_price": 8.50,
        "margin_percentage": 40,
        "stock": 150,
    },
    {
        "name": "Botella Térmica de Acero Inoxidable 750ml",
        "description": "Botella térmica que mantiene tus bebidas frías por 24h o calientes por 12h. Diseño elegante y ecológico.",
        "category": "Hogar",
        "images": ["https://picsum.photos/seed/bottle1/600/600"],
        "base_price": 15.00,
        "margin_percentage": 35,
        "stock": 90,
    },
    {
        "name": "Soporte Ajustable para Laptop",
        "description": "Soporte plegable de aluminio para laptop de hasta 17 pulgadas. Altura ajustable para mejorar tu postura al trabajar.",
        "category": "Accesorios",
        "images": ["https://picsum.photos/seed/stand1/600/600"],
        "base_price": 19.00,
        "margin_percentage": 35,
        "stock": 45,
    },
]


async def seed():
    await create_tables()
    async with async_session() as session:
        for data in PRODUCTS:
            selling = calc_selling_price(data["base_price"], data["margin_percentage"])
            product = Product(
                name=data["name"],
                description=data["description"],
                category=data["category"],
                images=data["images"],
                base_price=data["base_price"],
                margin_percentage=data["margin_percentage"],
                selling_price=selling,
                stock=data["stock"],
            )
            session.add(product)
            print(f"  ✓ {data['name']} — S/{selling:.2f} (costo S/{data['base_price']:.2f}, margen {data['margin_percentage']}%)")
        await session.commit()
    print("\n✅ Seed completado: 8 productos creados")


if __name__ == "__main__":
    asyncio.run(seed())
