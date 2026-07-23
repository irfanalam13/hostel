"use client"

import { useState } from "react"
import { getActiveAssignmentByStudent, endBedAssignment } from "@/features/beds/api/bed.api"
import { updateStudentPartial } from "@/features/students/api/student.api"
import { getStudentLedgers } from "@/features/fees/api/fee-ledger.api"
import { Button } from "@hostel/ui"
import { useToast } from "@hostel/ui"

export default function VacateStudentButton({
  studentId,
  onVacated,
}: {
  studentId: string
  onVacated: () => void
}) {
  const toast = useToast()
  const [loading, setLoading] = useState(false)

  const vacate = async () => {
    if (loading) return
    setLoading(true)
    try {
      // 1) STRICT RULE: Dues must be cleared
      const ledgers = await getStudentLedgers(studentId)
      const unpaid = ledgers.filter((l) => l.status === "DUE" || l.status === "PARTIAL")

      if (unpaid.length > 0) {
        toast.warning(
          `Student has ${unpaid.length} unpaid ledger(s). Clear dues first.`,
          "Cannot vacate"
        )
        return
      }

      // 2) End active bed assignment (if any)
      const active = await getActiveAssignmentByStudent(studentId)
      if (active) {
        await endBedAssignment(active.id, {
          is_active: false,
          end_date: new Date().toISOString().slice(0, 10),
        })
      }

      // 3) Mark student as former resident (LEFT)
      await updateStudentPartial(studentId, { status: "LEFT" })

      // 4) Refresh
      onVacated()
      toast.success("Student vacated (moved to Former).")
    } catch (e: any) {
      toast.error(e?.message || e?.response?.data?.detail || "Vacate failed.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Button variant="ghost" onClick={vacate} loading={loading} title="Vacate requires dues cleared">
      {loading ? "Vacating…" : "Vacate"}
    </Button>
  )
}
