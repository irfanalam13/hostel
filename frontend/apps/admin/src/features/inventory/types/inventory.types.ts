export type Money = string;

export type ItemType =
  | "consumable"
  | "non_consumable"
  | "asset"
  | "service"
  | "spare_part";

export type AssetStatus =
  | "available"
  | "assigned"
  | "in_maintenance"
  | "lost"
  | "damaged"
  | "retired"
  | "disposed";

export type AssetCondition = "new" | "good" | "fair" | "poor" | "unusable";

export type MovementType =
  | "purchase"
  | "sales"
  | "transfer"
  | "maintenance"
  | "allocation"
  | "consumption"
  | "return"
  | "adjustment"
  | "damage"
  | "lost"
  | "write_off";

export type PurchaseOrderStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "ordered"
  | "partially_received"
  | "fully_received"
  | "closed"
  | "cancelled";

export type ItemCategory = {
  id: string;
  name: string;
  parent: string | null;
  parent_name: string | null;
  description: string;
  is_system: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Brand = {
  id: string;
  name: string;
  manufacturer: string;
  website: string;
  is_active: boolean;
};

export type UnitOfMeasure = {
  id: string;
  name: string;
  symbol: string;
  factor: string;
  is_base: boolean;
  is_system: boolean;
};

export type Item = {
  id: string;
  item_code: string;
  sku: string;
  barcode: string;
  qr_code: string;
  name: string;
  description: string;
  category: string | null;
  category_name: string | null;
  brand: string | null;
  brand_name: string | null;
  model: string;
  manufacturer: string;
  item_type: ItemType;
  stock_uom: string | null;
  purchase_uom: string | null;
  min_stock: string;
  max_stock: string;
  reorder_level: string;
  safety_stock: string;
  purchase_price: Money;
  selling_price: Money;
  average_cost: Money;
  standard_cost: Money;
  tax_rate: string;
  discount: string;
  valuation_method: string;
  track_serial: boolean;
  track_batch: boolean;
  track_expiry: boolean;
  warranty_months: number;
  default_warehouse: string | null;
  rfid_tag: string;
  is_active: boolean;
  on_hand: string;
  created_at: string;
  updated_at: string;
};

export type ItemPayload = Partial<Omit<Item, "id" | "item_code" | "average_cost" | "on_hand">> & {
  name: string;
};

export type Warehouse = {
  id: string;
  name: string;
  warehouse_type: string;
  capacity: number;
  temperature: string;
  security_level: string;
  address: string;
  is_default: boolean;
  is_active: boolean;
};

export type StorageLocation = {
  id: string;
  warehouse: string;
  warehouse_name: string | null;
  name: string;
  zone: string;
  rack: string;
  shelf: string;
  bin: string;
  room: string | null;
  is_active: boolean;
};

export type StockLevel = {
  id: string;
  item: string;
  item_name: string | null;
  item_code: string | null;
  warehouse: string;
  warehouse_name: string | null;
  location: string | null;
  quantity_on_hand: string;
  quantity_reserved: string;
  quantity_allocated: string;
  quantity_available: string;
};

export type StockMovement = {
  id: string;
  reference: string;
  item: string;
  item_name: string | null;
  warehouse: string;
  warehouse_name: string | null;
  location: string | null;
  movement_type: MovementType;
  direction: "in" | "out";
  quantity: string;
  unit_cost: Money;
  reason: string;
  note: string;
  occurred_at: string;
  created_at: string;
};

export type Vendor = {
  id: string;
  vendor_code: string;
  company_name: string;
  contact_person: string;
  email: string;
  phone: string;
  website: string;
  address: string;
  tax_number: string;
  pan_vat: string;
  payment_terms: string;
  bank_details: Record<string, unknown>;
  rating: string;
  is_blacklisted: boolean;
  is_active: boolean;
};

export type PurchaseOrderLine = {
  id: string;
  item: string;
  item_name: string | null;
  description: string;
  ordered_quantity: string;
  received_quantity: string;
  unit_price: Money;
  tax_rate: string;
  discount: Money;
  line_total: Money;
  outstanding_quantity: string;
};

export type PurchaseOrder = {
  id: string;
  po_number: string;
  vendor: string;
  vendor_name: string | null;
  warehouse: string | null;
  status: PurchaseOrderStatus;
  order_date: string;
  expected_date: string | null;
  subtotal: Money;
  tax_total: Money;
  discount_total: Money;
  total: Money;
  notes: string;
  approved_at: string | null;
  lines: PurchaseOrderLine[];
  created_at: string;
  updated_at: string;
};

export type CreatePurchaseOrderPayload = {
  vendor: string;
  warehouse?: string | null;
  expected_date?: string | null;
  notes?: string;
  lines: {
    item: string;
    description?: string;
    ordered_quantity: string;
    unit_price: string;
    tax_rate?: string;
    discount?: string;
  }[];
};

export type GoodsReceipt = {
  id: string;
  grn_number: string;
  purchase_order: string;
  warehouse: string;
  received_date: string;
  note: string;
  lines: {
    id: string;
    item: string;
    item_name: string | null;
    quantity: string;
    unit_cost: Money;
    batch_number: string;
  }[];
};

export type Asset = {
  id: string;
  asset_tag: string;
  barcode: string;
  qr_code: string;
  name: string;
  item: string | null;
  category: string | null;
  category_name: string | null;
  serial_number: string;
  purchase_date: string | null;
  purchase_cost: Money;
  vendor: string | null;
  vendor_name: string | null;
  warranty_until: string | null;
  insurance: Record<string, unknown>;
  useful_life_months: number;
  salvage_value: Money;
  depreciation_method: string;
  accounting_asset: string | null;
  status: AssetStatus;
  condition: AssetCondition;
  department: string;
  warehouse: string | null;
  location: string | null;
  assigned_room: string | null;
  assigned_bed: string | null;
  assigned_resident: string | null;
  assigned_student: string | null;
  assigned_staff: string | null;
  iot_device_id: string;
  created_at: string;
  updated_at: string;
};

export type AssetPayload = Partial<Omit<Asset, "id" | "asset_tag" | "status">> & {
  name: string;
};

export type AssetLifecycleEvent = {
  id: string;
  asset: string;
  stage: string;
  cost: Money;
  complaint: string | null;
  note: string;
  occurred_at: string;
};

export type InventoryDashboard = {
  totals: {
    inventory_value: Money;
    total_items: number;
    active_items: number;
    total_assets: number;
    active_assets: number;
    inactive_assets: number;
    maintenance_assets: number;
    damaged_assets: number;
    low_stock: number;
    out_of_stock: number;
    overstock: number;
    total_vendors: number;
    open_purchase_orders: number;
    pending_deliveries: number;
  };
  movement_trend: { month: string | null; direction: "in" | "out"; quantity: string }[];
  by_category: { category: string; count: number }[];
  recent_movements: StockMovement[];
};
