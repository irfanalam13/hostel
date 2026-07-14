import { apiDownload, apiFetch } from "@hostel/api";

import type {
  Asset,
  AssetLifecycleEvent,
  AssetPayload,
  Brand,
  CreatePurchaseOrderPayload,
  GoodsReceipt,
  InventoryDashboard,
  Item,
  ItemCategory,
  ItemPayload,
  PurchaseOrder,
  StockLevel,
  StockMovement,
  StorageLocation,
  UnitOfMeasure,
  Vendor,
  Warehouse,
} from "../types/inventory.types";

function f<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/inventory${path}`, options);
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

type QueryValue = string | number | boolean | undefined | null;

function qs(params: Record<string, QueryValue>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== "",
  );
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");
}

export const inventoryApi = {
  dashboard: {
    summary: () => f<InventoryDashboard>("/dashboard/summary/"),
  },

  categories: {
    list: (params: Record<string, QueryValue> = {}) => f<ItemCategory[]>(`/categories/${qs(params)}`),
    create: (body: Partial<ItemCategory>) => f<ItemCategory>("/categories/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<ItemCategory>) =>
      f<ItemCategory>(`/categories/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/categories/${id}/`, { method: "DELETE" }),
  },

  brands: {
    list: (params: Record<string, QueryValue> = {}) => f<Brand[]>(`/brands/${qs(params)}`),
    create: (body: Partial<Brand>) => f<Brand>("/brands/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Brand>) => f<Brand>(`/brands/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/brands/${id}/`, { method: "DELETE" }),
  },

  units: {
    list: (params: Record<string, QueryValue> = {}) => f<UnitOfMeasure[]>(`/units/${qs(params)}`),
    create: (body: Partial<UnitOfMeasure>) => f<UnitOfMeasure>("/units/", { method: "POST", ...json(body) }),
    remove: (id: string) => f<void>(`/units/${id}/`, { method: "DELETE" }),
  },

  items: {
    list: (params: Record<string, QueryValue> = {}) => f<Item[]>(`/items/${qs(params)}`),
    retrieve: (id: string) => f<Item>(`/items/${id}/`),
    create: (body: ItemPayload) => f<Item>("/items/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<ItemPayload>) => f<Item>(`/items/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/items/${id}/`, { method: "DELETE" }),
    adjustStock: (id: string, body: { warehouse: string; location?: string | null; target_quantity: string; reason?: string }) =>
      f<StockMovement>(`/items/${id}/adjust-stock/`, { method: "POST", ...json(body) }),
    transfer: (id: string, body: { from_warehouse: string; to_warehouse: string; quantity: string; note?: string }) =>
      f<StockMovement[]>(`/items/${id}/transfer/`, { method: "POST", ...json(body) }),
    issue: (id: string, body: Record<string, unknown>) =>
      f<StockMovement>(`/items/${id}/issue/`, { method: "POST", ...json(body) }),
    movements: (id: string) => f<StockMovement[]>(`/items/${id}/movements/`),
  },

  warehouses: {
    list: (params: Record<string, QueryValue> = {}) => f<Warehouse[]>(`/warehouses/${qs(params)}`),
    create: (body: Partial<Warehouse>) => f<Warehouse>("/warehouses/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Warehouse>) =>
      f<Warehouse>(`/warehouses/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/warehouses/${id}/`, { method: "DELETE" }),
  },

  locations: {
    list: (params: Record<string, QueryValue> = {}) => f<StorageLocation[]>(`/locations/${qs(params)}`),
    create: (body: Partial<StorageLocation>) => f<StorageLocation>("/locations/", { method: "POST", ...json(body) }),
    remove: (id: string) => f<void>(`/locations/${id}/`, { method: "DELETE" }),
  },

  stockLevels: {
    list: (params: Record<string, QueryValue> = {}) => f<StockLevel[]>(`/stock-levels/${qs(params)}`),
  },

  movements: {
    list: (params: Record<string, QueryValue> = {}) => f<StockMovement[]>(`/movements/${qs(params)}`),
  },

  vendors: {
    list: (params: Record<string, QueryValue> = {}) => f<Vendor[]>(`/vendors/${qs(params)}`),
    create: (body: Partial<Vendor>) => f<Vendor>("/vendors/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<Vendor>) => f<Vendor>(`/vendors/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/vendors/${id}/`, { method: "DELETE" }),
  },

  purchaseOrders: {
    list: (params: Record<string, QueryValue> = {}) => f<PurchaseOrder[]>(`/purchase-orders/${qs(params)}`),
    retrieve: (id: string) => f<PurchaseOrder>(`/purchase-orders/${id}/`),
    create: (body: CreatePurchaseOrderPayload) =>
      f<PurchaseOrder>("/purchase-orders/", { method: "POST", ...json(body) }),
    remove: (id: string) => f<void>(`/purchase-orders/${id}/`, { method: "DELETE" }),
    submit: (id: string) => f<PurchaseOrder>(`/purchase-orders/${id}/submit/`, { method: "POST", ...json({}) }),
    approve: (id: string) => f<PurchaseOrder>(`/purchase-orders/${id}/approve/`, { method: "POST", ...json({}) }),
    cancel: (id: string) => f<PurchaseOrder>(`/purchase-orders/${id}/cancel/`, { method: "POST", ...json({}) }),
    receive: (
      id: string,
      body: { warehouse?: string | null; received_date?: string | null; note?: string; lines: { item: string; po_line?: string | null; quantity: string; unit_cost?: string | null; batch_number?: string }[] },
    ) => f<GoodsReceipt>(`/purchase-orders/${id}/receive/`, { method: "POST", ...json(body) }),
  },

  goodsReceipts: {
    list: (params: Record<string, QueryValue> = {}) => f<GoodsReceipt[]>(`/goods-receipts/${qs(params)}`),
  },

  assets: {
    list: (params: Record<string, QueryValue> = {}) => f<Asset[]>(`/assets/${qs(params)}`),
    retrieve: (id: string) => f<Asset>(`/assets/${id}/`),
    create: (body: AssetPayload) => f<Asset>("/assets/", { method: "POST", ...json(body) }),
    update: (id: string, body: Partial<AssetPayload>) => f<Asset>(`/assets/${id}/`, { method: "PATCH", ...json(body) }),
    remove: (id: string) => f<void>(`/assets/${id}/`, { method: "DELETE" }),
    assign: (id: string, body: Record<string, unknown>) =>
      f<Asset>(`/assets/${id}/assign/`, { method: "POST", ...json(body) }),
    returnAsset: (id: string, note = "") =>
      f<Asset>(`/assets/${id}/return/`, { method: "POST", ...json({ note }) }),
    changeStatus: (id: string, body: { status: string; note?: string; cost?: string }) =>
      f<Asset>(`/assets/${id}/change-status/`, { method: "POST", ...json(body) }),
    depreciate: (id: string) =>
      f<{ detail: string }>(`/assets/${id}/depreciate/`, { method: "POST", ...json({}) }),
    history: (id: string) => f<AssetLifecycleEvent[]>(`/assets/${id}/history/`),
  },

  reports: {
    stockSummary: () => f<{ headers: string[]; rows: string[][] }>("/reports/stock-summary/"),
    valuation: () => f<{ items: Record<string, string>[]; total_value: string }>("/reports/valuation/"),
    lowStock: () => f<{ items: Record<string, string>[] }>("/reports/low-stock/"),
    exportCsv: (type = "stock-summary") =>
      apiDownload(`/inventory/reports/export/${qs({ type, fmt: "csv" })}`, `inventory-${type}.csv`),
    exportXlsx: (type = "stock-summary") =>
      apiDownload(`/inventory/reports/export/${qs({ type, fmt: "xlsx" })}`, `inventory-${type}.xlsx`),
  },
};
