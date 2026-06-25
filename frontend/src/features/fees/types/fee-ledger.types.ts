export type LedgerStatus = "DUE" | "PARTIAL" | "PAID"

export interface FeeLedger {
  id: string
  student: string
  month?: string
  amount?: string
  discount?: string
  fine?: string
  net_due: string // Decimal as string
  status: LedgerStatus
  notes?: string
  created_at?: string
}
