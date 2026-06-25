"use client"

import { useEffect, useCallback, useState } from "react"
import { useParams } from "next/navigation"

import { getStudent } from "@/features/students/api/student.api"
import { Student } from "@/features/students/types/student.types"

import StudentDocuments from "@/features/students/components/StudentDocuments"
import AssignBed from "@/features/students/components/AssignBed"
import VacateStudentButton from "@/features/students/components/VacateStudentButton"

import StudentDuesCard from "@/features/payments/components/StudentDuesCard"
import StudentPayments from "@/features/payments/components/StudentPayments"

export default function StudentDetailPage() {
  const params = useParams()
  const id = params?.id as string | undefined

  const [student, setStudent] = useState<Student | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const s = await getStudent(id)
      setStudent(s)
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load student.")
      setStudent(null)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    refresh()
  }, [refresh])

  if (loading) return <p className="p-6">Loading...</p>

  if (error) {
    return (
      <div className="p-6">
        <p className="text-red-600">{error}</p>
        <button className="border px-3 py-2 rounded mt-3" onClick={refresh}>
          Retry
        </button>
      </div>
    )
  }

  if (!student) return <p className="p-6">Student not found.</p>

  return (
    <div className="p-6">
      {/* HEADER */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{student.full_name}</h1>
          <p>Phone: {student.phone}</p>
          <p>Guardian: {student.guardian_phone}</p>
          <p>
            Status:{" "}
            <span
              className={`font-semibold ${
                student.status === "ACTIVE"
                  ? "text-green-600"
                  : "text-red-600"
              }`}
            >
              {student.status}
            </span>
          </p>
        </div>

        {/* Vacate rule:
           - blocks if any ledger status = DUE or PARTIAL
           - ends active BedAssignment
           - sets student.status = INACTIVE
        */}
        <VacateStudentButton
          studentId={student.id}
          onVacated={refresh}
        />
      </div>

      {/* Bed Assignment (uses BedAssignmentViewSet) */}
      <AssignBed studentId={student.id} />

      {/* Documents */}
      <StudentDocuments student={student} />

      {/* Dues Summary (based on /ledgers/) */}
      <StudentDuesCard studentId={student.id} />

      {/* Payments (allocations strict + receipt) */}
      <StudentPayments studentId={student.id} />
    </div>
  )
}