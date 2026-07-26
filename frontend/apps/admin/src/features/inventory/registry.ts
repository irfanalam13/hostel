import type { ComponentType } from "react";
import {
  Boxes,
  ClipboardList,
  LayoutDashboard,
  Package,
  PackageSearch,
  ShoppingCart,
  Tags,
  Truck,
  Warehouse,
} from "lucide-react";

export type InventorySection = {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
};

/** Single source of truth for the Inventory module sub-navigation. */
export const INVENTORY_SECTIONS: InventorySection[] = [
  {
    id: "overview",
    label: "Overview",
    description: "Stock value, assets and procurement at a glance",
    href: "/inventory",
    icon: LayoutDashboard,
  },
  {
    id: "items",
    label: "Items",
    description: "The item master catalog",
    href: "/inventory/items",
    icon: Package,
  },
  {
    id: "stock",
    label: "Stock",
    description: "On-hand levels across warehouses",
    href: "/inventory/stock",
    icon: PackageSearch,
  },
  {
    id: "movements",
    label: "Movements",
    description: "Every stock in/out movement",
    href: "/inventory/movements",
    icon: ClipboardList,
  },
  {
    id: "warehouses",
    label: "Warehouses",
    description: "Warehouses and storage locations",
    href: "/inventory/warehouses",
    icon: Warehouse,
  },
  {
    id: "vendors",
    label: "Vendors",
    description: "Suppliers and vendor performance",
    href: "/inventory/vendors",
    icon: Truck,
  },
  {
    id: "purchase-orders",
    label: "Purchase Orders",
    description: "Procurement and goods receipt",
    href: "/inventory/purchase-orders",
    icon: ShoppingCart,
  },
  {
    id: "assets",
    label: "Assets",
    description: "Asset register and lifecycle",
    href: "/inventory/assets",
    icon: Boxes,
  },
  {
    id: "categories",
    label: "Catalog",
    description: "Categories, brands and units",
    href: "/inventory/categories",
    icon: Tags,
  },
  {
    id: "reports",
    label: "Reports",
    description: "Valuation, low-stock and exports",
    href: "/inventory/reports",
    icon: ClipboardList,
  },
];
