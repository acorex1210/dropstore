export interface Product {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  images: string[];
  base_price: number;
  margin_percentage: number;
  selling_price: number;
  stock: number;
  is_active: boolean;
  provider_name: string;
  variants: ProductVariant[];
  created_at: string;
  updated_at: string;
}

export interface ProductListItem {
  id: string;
  name: string;
  category: string | null;
  images: string[];
  selling_price: number;
  stock: number;
  margin_percentage: number;
}

export interface ProductVariant {
  id: string;
  name: string;
  sku: string | null;
  base_price: number | null;
  selling_price: number | null;
  stock: number;
  attributes: Record<string, string>;
}

export interface CartItem {
  product_id: string;
  product_name: string;
  product_image: string;
  selling_price: number;
  quantity: number;
}

export interface CheckoutRequest {
  items: { product_id: string; variant_id: string | null; quantity: number }[];
  email: string;
  full_name: string;
  phone: string;
  address: string;
  city: string;
  department: string;
  country: string;
  notes: string;
}

export interface PreferenceResponse {
  preference_id: string;
  init_point: string;
  order_id: string;
  total: number;
}

export interface Order {
  id: string;
  customer_id: string;
  status: string;
  subtotal: number;
  shipping_cost: number;
  total_amount: number;
  total_cost: number;
  total_margin: number;
  currency: string;
  payment_id: string | null;
  payment_status: string | null;
  provider_order_id: string | null;
  tracking_number: string | null;
  tracking_url: string | null;
  shipping_address: string;
  shipping_city: string;
  shipping_department: string | null;
  items: OrderItem[];
  created_at: string;
}

export interface OrderItem {
  id: string;
  product_name: string;
  variant_name: string | null;
  quantity: number;
  unit_price: number;
  unit_cost: number;
  subtotal: number;
  margin: number;
}

export interface StatsSummary {
  total_orders: number;
  total_revenue: number;
  total_cost: number;
  total_margin: number;
  avg_margin_pct: number;
  paid_pending: number;
  processing: number;
  shipped: number;
  delivered: number;
  cancelled: number;
  today_revenue: number;
  today_orders: number;
}

export interface TopProduct {
  product_id: string;
  product_name: string;
  total_sold: number;
  total_revenue: number;
  total_cost: number;
  total_margin: number;
}

export interface SalesReportRow {
  period: string;
  orders: number;
  revenue: number;
  cost: number;
  margin: number;
  avg_order: number;
}

export interface ProfitByProduct {
  product_id: string;
  product_name: string;
  units_sold: number;
  revenue: number;
  cost: number;
  margin: number;
  margin_pct: number;
}

export interface ProfitByMonth {
  year_month: string;
  orders: number;
  revenue: number;
  cost: number;
  margin: number;
  margin_pct: number;
}

export interface ProfitReport {
  products: ProfitByProduct[];
  months: ProfitByMonth[];
  totals: {
    revenue: number;
    cost: number;
    margin: number;
    margin_pct: number;
  };
}
