"use client"

import { useEffect, useState } from "react"
import { getStudentLedgers } from "@/features/fees/api/fee-ledger.api"
import { FeeLedger } from "@/features/fees/types/fee-ledger.types"
import { computeDues } from "../utils/dues"

export default function StudentDuesCard({ studentId }: { studentId: string }) {
  const [ledgers, setLedgers] = useState<FeeLedger[]>([])

  useEffect(() => {
    getStudentLedgers(studentId).then(setLedgers).catch(() => setLedgers([]))
  }, [studentId])

  const { totalDue, unpaidTotal, unpaidCount } = computeDues(ledgers)

  return (
    <div className="border rounded p-4 mt-4">
      <div className="font-semibold mb-2">Dues Summary</div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
        <div className="border rounded p-3">
          <div className="text-gray-600">Total Net Due</div>
          <div className="font-bold">Rs {totalDue}</div>
        </div>

        <div className="border rounded p-3">
          <div className="text-gray-600">Unpaid Ledgers</div>
          <div className="font-bold">{unpaidCount}</div>
        </div>

        <div className="border rounded p-3">
          <div className="text-gray-600">Unpaid Amount</div>
          <div className="font-bold">Rs {unpaidTotal}</div>
        </div>
      </div>

      <div className="text-xs text-gray-600 mt-2">
        *Based on FeeLedger status (DUE/PARTIAL/PAID) and net_due.
      </div>
    </div>
  )
}
