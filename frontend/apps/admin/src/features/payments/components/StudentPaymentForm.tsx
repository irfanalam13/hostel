"use client"

import { useEffect, useMemo, useState } from "react"
import { getStudentLedgers } from "@/features/fees/api/fee-ledger.api"
import { FeeLedger } from "@/features/fees/types/fee-ledger.types"
import { createPayment } from "../api/payment.api"
import { PaymentCreateAllocationInput } from "../types/payment.types"

function to2(n: number) {
  return n.toFixed(2)
}

export default function StudentPaymentForm({
  studentId,
  onCreated,
}: {
  studentId: string
  onCreated: () => void
}) {
  const [ledgers, setLedgers] = useState<FeeLedger[]>([])
  const [amount, setAmount] = useState("")
  const [method, setMethod] = useState("CASH")
  const [referenceNo, setReferenceNo] = useState("")
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [allocMap, setAllocMap] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getStudentLedgers(studentId).then(setLedgers).catch(() => setLedgers([]))
  }, [studentId])

  const dueLedgers = useMemo(
    () => ledgers.filter((l) => l.status === "DUE" || l.status === "PARTIAL"),
    [ledgers]
  )

  const allocatedTotal = useMemo(() => {
    let t = 0
    for (const v of Object.values(allocMap)) t += Number(v || "0")
    return t
  }, [allocMap])

  const onAutoAllocate = () => {
    const pay = Number(amount || "0")
    if (!pay || dueLedgers.length === 0) return

    // Simple allocation: fill ledgers in order (max = net_due)
    let remaining = pay
    const next: Record<string, string> = {}

    for (const l of dueLedgers) {
      if (remaining <= 0) break
      const need = Number(l.net_due || "0")
      const use = Math.min(need, remaining)
      next[l.id] = to2(use)
      remaining -= use
    }

    setAllocMap(next)
  }

  const submit = async () => {
    setError(null)
    const pay = Number(amount || "0")

    if (pay <= 0) return setError("Enter valid payment amount.")
    if (dueLedgers.length === 0) return setError("No DUE/PARTIAL ledgers found to allocate.")

    // Build allocations list in serializer-required shape
    const allocations: PaymentCreateAllocationInput[] = Object.entries(allocMap)
      .filter(([_, v]) => Number(v || "0") > 0)
      .map(([ledgerId, v]) => ({ ledger_id: ledgerId, amount: to2(Number(v)) }))

    const total = allocations.reduce((s, a) => s + Number(a.amount || "0"), 0)

    // Must match service strict rule
    if (to2(total) !== to2(pay)) {
      return setError(`Allocated total (Rs ${to2(total)}) must equal payment amount (Rs ${to2(pay)}).`)
    }

    setLoading(true)
    try {
      await createPayment({
        student: studentId,
        amount: to2(pay),
        date,
        method,
        reference_no: referenceNo || "",
        allocations,
      })
      setAmount("")
      setReferenceNo("")
      setAllocMap({})
      onCreated()
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Payment create failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border rounded p-4 mt-4">
      <div className="font-semibold mb-2">Add Payment (with allocations)</div>

      {error && <div className="mb-3 text-sm text-red-600">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3">
        <input className="border p-2 rounded" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <input className="border p-2 rounded" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <select className="border p-2 rounded" value={method} onChange={(e) => setMethod(e.target.value)}>
          <option value="CASH">CASH</option>
          <option value="ESEWA">ESEWA</option>
          <option value="KHALTI">KHALTI</option>
          <option value="BANK">BANK</option>
        </select>
        <input className="border p-2 rounded" placeholder="Reference No" value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} />
      </div>

      <div className="flex items-center gap-2 mb-3">
        <button className="border px-3 py-2 rounded" onClick={onAutoAllocate} disabled={!amount || dueLedgers.length === 0}>
          Auto allocate
        </button>
        <div className="text-sm text-gray-600">
          Allocated total: <span className="font-semibold">Rs {to2(allocatedTotal)}</span>
        </div>
      </div>

      <div className="border rounded p-3">
        <div className="font-semibold text-sm mb-2">Allocate to ledgers (DUE/PARTIAL)</div>

        {dueLedgers.length === 0 ? (
          <div className="text-sm text-gray-600">No due ledgers found.</div>
        ) : (
          <div className="space-y-2">
            {dueLedgers.map((l) => (
              <div key={l.id} className="flex flex-col md:flex-row md:items-center gap-2 border rounded p-2">
                <div className="flex-1 text-sm">
                  <div className="font-semibold">Ledger #{l.id}</div>
                  <div className="text-gray-600">Net Due: Rs {l.net_due} • Status: {l.status}</div>
                </div>
                <input
                  className="border p-2 rounded w-full md:w-48"
                  placeholder="Allocate amount"
                  value={allocMap[l.id] ?? ""}
                  onChange={(e) => setAllocMap({ ...allocMap, [l.id]: e.target.value })}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="border px-3 py-2 rounded mt-3" onClick={submit} disabled={loading}>
        {loading ? "Saving..." : "Create Payment"}
      </button>

      <div className="text-xs text-gray-600 mt-2">
        *Backend requires allocations total == payment.amount (strict).
      </div>
    </div>
  )
}
