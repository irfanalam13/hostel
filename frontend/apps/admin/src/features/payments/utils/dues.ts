import { FeeLedger } from "@/features/fees/types/fee-ledger.types"

export function sumDecimalStrings(values: string[]) {
  // safe decimal sum (no float)
  let total = 0
  for (const v of values) total += Number(v || "0")
  // backend uses decimals; for UI we keep 2 decimals
  return total.toFixed(2)
}

export function computeDues(ledgers: FeeLedger[]) {
  const totalDue = sumDecimalStrings(ledgers.map((l) => l.net_due))
  const unpaidLedgers = ledgers.filter((l) => l.status === "DUE" || l.status === "PARTIAL")
  const unpaidTotal = sumDecimalStrings(unpaidLedgers.map((l) => l.net_due))
  return { totalDue, unpaidTotal, unpaidCount: unpaidLedgers.length }
}