import Link from "next/link"
import { Student } from "../types/student.types"

import type { BedAssignment } from "@/features/beds/types/bed.types"
import VacateStudentButton from "@/features/students/components/VacateStudentButton"

type DuesSummary = {
  unpaidCount: number
  unpaidAmount: string
}

function StatusBadge({ status }: { status: Student["status"] }) {
  const isActive = status === "ACTIVE"
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold",
        isActive ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700",
      ].join(" ")}
    >
      {status}
    </span>
  )
}

function DuesBadge({
  dues,
  loading,
}: {
  dues?: DuesSummary
  loading?: boolean
}) {
  if (loading) {
    return (
      <span className="inline-flex items-center rounded-full px-2 py-1 text-xs bg-gray-100 text-gray-600">
        Loading dues...
      </span>
    )
  }
  if (!dues) return <span className="text-gray-500">—</span>

  const hasDue = dues.unpaidCount > 0 && Number(dues.unpaidAmount) > 0
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold",
        hasDue ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-700",
      ].join(" ")}
      title={hasDue ? "Has unpaid dues" : "No dues"}
    >
      {hasDue ? `${dues.unpaidCount} due • Rs ${dues.unpaidAmount}` : "Clear"}
    </span>
  )
}

export default function StudentTable({
  students,
  duesMap,
  duesLoading,
  activeAssignmentByStudent,
  bedLabelById,
  onRefresh,
}: {
  students: Student[]
  duesMap: Record<string, DuesSummary>
  duesLoading: boolean
  activeAssignmentByStudent: Record<string, BedAssignment | undefined>
  bedLabelById: Record<string, string>
  onRefresh: () => void
}) {
  if (!students || students.length === 0) {
    return (
      <div className="border rounded p-4 text-sm text-gray-600">
        No students found.
      </div>
    )
  }

  return (
    <div className="border rounded overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr className="text-left">
            <th className="p-3">Student</th>
            <th className="p-3">Bed</th>
            <th className="p-3">Dues</th>
            <th className="p-3">Status</th>
            <th className="p-3 text-right">Actions</th>
          </tr>
        </thead>

        <tbody>
          {students.map((s) => {
            const a = activeAssignmentByStudent[s.id]
            const bedLabel = a ? bedLabelById[a.bed] || `Bed #${a.bed}` : "—"
            const dues = duesMap[s.id]

            return (
              <tr key={s.id} className="border-b last:border-b-0">
                <td className="p-3">
                  <div className="font-semibold">{s.full_name}</div>
                  <div className="text-xs text-gray-500">{s.phone || "—"}</div>
                </td>

                <td className="p-3">
                  <div className="font-medium">{bedLabel}</div>
                  {a?.start_date ? (
                    <div className="text-xs text-gray-500">Since {a.start_date}</div>
                  ) : null}
                </td>

                <td className="p-3">
                  <DuesBadge dues={dues} loading={duesLoading} />
                </td>

                <td className="p-3">
                  <StatusBadge status={s.status} />
                </td>

                <td className="p-3">
                  <div className="flex justify-end gap-3 items-center">
                    <Link
                      href={`/students/${s.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      View
                    </Link>

                    {/* Vacate:
                        - blocks if ledgers have DUE/PARTIAL
                        - ends active bed assignment
                        - marks student INACTIVE
                        refreshes list after success
                    */}
                    <VacateStudentButton
                      studentId={s.id}
                      onVacated={onRefresh}
                    />
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
