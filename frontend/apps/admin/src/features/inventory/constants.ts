import type {
  AssetCondition,
  AssetStatus,
  ItemType,
  MovementType,
  PurchaseOrderStatus,
} from "./types/inventory.types";

type Option<T extends string> = { value: T; label: string };

export const ITEM_TYPES: Option<ItemType>[] = [
  { value: "consumable", label: "Consumable" },
  { value: "non_consumable", label: "Non-Consumable" },
  { value: "asset", label: "Asset" },
  { value: "service", label: "Service" },
  { value: "spare_part", label: "Spare Part" },
];

export const ASSET_STATUSES: Option<AssetStatus>[] = [
  { value: "available", label: "Available" },
  { value: "assigned", label: "Assigned" },
  { value: "in_maintenance", label: "In Maintenance" },
  { value: "lost", label: "Lost" },
  { value: "damaged", label: "Damaged" },
  { value: "retired", label: "Retired" },
  { value: "disposed", label: "Disposed" },
];

export const ASSET_CONDITIONS: Option<AssetCondition>[] = [
  { value: "new", label: "New" },
  { value: "good", label: "Good" },
  { value: "fair", label: "Fair" },
  { value: "poor", label: "Poor" },
  { value: "unusable", label: "Unusable" },
];

export const DEPRECIATION_METHODS = [
  { value: "none", label: "None" },
  { value: "straight_line", label: "Straight Line" },
  { value: "declining", label: "Declining Balance" },
];

export const MOVEMENT_TYPES: Option<MovementType>[] = [
  { value: "purchase", label: "Purchase / Receipt" },
  { value: "consumption", label: "Consumption" },
  { value: "allocation", label: "Allocation" },
  { value: "transfer", label: "Internal Transfer" },
  { value: "maintenance", label: "Maintenance Usage" },
  { value: "return", label: "Return" },
  { value: "adjustment", label: "Adjustment" },
  { value: "damage", label: "Damage" },
  { value: "lost", label: "Lost" },
  { value: "write_off", label: "Write-Off" },
];

export const WAREHOUSE_TYPES = [
  { value: "main", label: "Main Warehouse" },
  { value: "kitchen", label: "Kitchen" },
  { value: "maintenance", label: "Maintenance" },
  { value: "laundry", label: "Laundry" },
  { value: "office", label: "Office" },
  { value: "branch", label: "Branch" },
];

export const PO_STATUS_LABELS: Record<PurchaseOrderStatus, string> = {
  draft: "Draft",
  pending_approval: "Pending Approval",
  approved: "Approved",
  ordered: "Ordered",
  partially_received: "Partially Received",
  fully_received: "Fully Received",
  closed: "Closed",
  cancelled: "Cancelled",
};
