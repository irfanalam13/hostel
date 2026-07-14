# Inventory & Asset Management (`apps.inventory`)

An ERP-style, multi-tenant inventory and asset module. Every row is scoped to
`tenants.Hostel` via `HostelScopedModel`; the API is RBAC-gated (`inventory.*`),
plan-gated behind the `inventory` feature, and audit-logged.

## Surface

- **Catalog & masters** — `ItemCategory` (nesting), `Brand`, `UnitOfMeasure`, `Item`.
- **Warehousing** — `Warehouse`, `StorageLocation`, `StockLevel` (source of truth
  for on-hand), `Batch`, `SerialUnit`.
- **Movements** — `StockMovement` (append-only ledger), `StockCount` cycle counts.
- **Procurement** — `Vendor`, `PurchaseOrder`(+lines), `GoodsReceipt`(+lines).
- **Assets** — `Asset` (native lifecycle) + `AssetAssignment` / `AssetLifecycleEvent`,
  optionally linked to `accounting.FixedAsset` for depreciation.

All business logic lives in `services.py`. Numbers (SKU/PO/GRN/asset tag/movement
ref) are minted per-workspace via `InventorySequence` / `services.next_number`.

## Integrations

- **Accounting / Finance (opt-in)** — `services.post_inventory_ledger` posts a
  balanced journal to `apps.accounting` on goods receipt / write-off **only when
  the `accounting` feature is enabled** for the workspace, plus a best-effort
  `finance.LedgerTransaction`. Wrapped so a ledger failure never rolls back the
  stock mutation. Depreciation delegates to `accounting.services.run_depreciation`.
- **Notifications** — low-stock / out-of-stock alerts go to MANAGER/ADMIN/OWNER via
  `apps.notifications.services.create_notification` (best-effort).
- **Maintenance** — spare-part usage and repairs link to `complaints.Complaint`
  (the de-facto maintenance ticket; no dedicated maintenance app exists yet).
- **Allocation** — issues attach to `rooms.Room` / `rooms.Bed` plus an optional
  occupant (`residents.Resident` or `students.Student`) — all nullable.

## Valuation

Weighted-average costing is implemented (`_recalc_average_cost`). FIFO / standard
cost are modelled on `Item.valuation_method` but not yet computed — extend
`apply_movement` to add lot-costing.

## Extension points (architected, not wired to hardware)

- `Item.rfid_tag`, `SerialUnit.nfc_id`, `Asset.iot_device_id` — RFID/NFC/IoT-ready
  identifier fields.
- `services.forecast_consumption(item)` — a deterministic historical-average
  forecast the future AI layer can replace.
- Barcode/QR values are stored on items/assets for client- or scanner-side
  rendering; server-side label image generation is a future addition.

## Testing

`apps/inventory/tests/` (pytest). The `inventory` feature is default-off in the
subscription catalog, so `tests/conftest.py` enables it via a `FeatureOverride`.
Ledger-bridge tests toggle `ENTITLEMENTS_ENFORCED=True` to exercise the
accounting-enabled / disabled paths.
