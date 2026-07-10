"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Topbar } from "@/components/shell/Topbar";

import { getStudents } from "@/features/students/api/student.api"
import { Student } from "@/features/students/types/student.types"

import StudentFilters from "@/features/students/components/StudentFilters"
import StudentTable from "@/features/students/components/StudentTable"

import { getBeds } from "@/features/beds/api/bed.api"
import { getActiveAssignments } from "@/features/beds/api/bed.api"
import type { Bed, BedAssignment } from "@/features/beds/types/bed.types"

import { getStudentLedgers } from "@/features/fees/api/fee-ledger.api"
import type { FeeLedger } from "@/features/fees/types/fee-ledger.types"

type DuesSummary = {
  unpaidCount: number
  unpaidAmount: string
}

function sum2(values: string[]) {
  let t = 0
  for (const v of values) t += Number(v || "0")
  return t.toFixed(2)
}

function computeDues(ledgers: FeeLedger[]): DuesSummary {
  const unpaid = ledgers.filter((l) => l.status === "DUE" || l.status === "PARTIAL")
  return {
    unpaidCount: unpaid.length,
    unpaidAmount: sum2(unpaid.map((l) => l.net_due)),
  }
}

export default function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([])
  const [beds, setBeds] = useState<Bed[]>([])
  const [activeAssignments, setActiveAssignments] = useState<BedAssignment[]>([])

  const [duesMap, setDuesMap] = useState<Record<string, DuesSummary>>({})
  const [duesLoading, setDuesLoading] = useState(false)

  const [search, setSearch] = useState("")
  const [status, setStatus] = useState<"" | "ACTIVE" | "INACTIVE">("")

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Debounce the search input: fetchAll fans out to students + beds +
  // assignments + one ledger call per student, so refetching on every
  // keystroke is a request storm. Wait for a typing pause instead.
  const [debouncedSearch, setDebouncedSearch] = useState("")
  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search), 350)
    return () => window.clearTimeout(t)
  }, [search])

  const params = useMemo(
    () => ({
      search: debouncedSearch.trim() || undefined,
      status: status || undefined,
    }),
    [debouncedSearch, status]
  )

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [stu, bedList, assigns] = await Promise.all([
        getStudents(params),
        getBeds(),
        getActiveAssignments(),
      ])

      setStudents(stu)
      setBeds(bedList)
      setActiveAssignments(assigns)

      // Dues: per student (no bulk endpoint in backend)
      setDuesLoading(true)
      const entries = await Promise.all(
        stu.map(async (s) => {
          const ledgers = await getStudentLedgers(s.id)
          return [s.id, computeDues(ledgers)] as const
        })
      )
      setDuesMap(Object.fromEntries(entries))
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load students.")
      setStudents([])
      setBeds([])
      setActiveAssignments([])
      setDuesMap({})
    } finally {
      setDuesLoading(false)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  // Map: bedId -> label
  const bedLabelById = useMemo(() => {
    const m: Record<string, string> = {}
    for (const b of beds) {
      // Bed has fields: room (id) + bed_no
      m[b.id] = `Room ${b.room} / Bed ${b.bed_no}`
    }
    return m
  }, [beds])

  // Map: studentId -> active assignment
  const activeAssignmentByStudent = useMemo(() => {
    const m: Record<string, BedAssignment> = {}
    for (const a of activeAssignments) m[a.student] = a
    return m
  }, [activeAssignments])

  return (
    <div className="p-6">
      <Topbar title="Students" />
      <div>Students page</div>
      <div className="flex items-center justify-between gap-3 mb-3">

        <h1 className="text-2xl font-bold">Students</h1>

        <div className="flex gap-2">
          <button className="border px-3 py-2 rounded" onClick={fetchAll} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>

          <Link className="border px-3 py-2 rounded" href="/students/new">
            + Add Student
          </Link>
        </div>
      </div>

      <StudentFilters
        search={search}
        status={status}
        onChange={(n) => {
          setSearch(n.search)
          setStatus(n.status)
        }}
      />

      {loading ? (
        <div className="text-sm text-gray-600">Loading students...</div>
      ) : error ? (
        <div className="border rounded p-4">
          <div className="text-red-600 text-sm">{error}</div>
          <button className="border px-3 py-2 rounded mt-3" onClick={fetchAll}>
            Retry
          </button>
        </div>
      ) : (
        <StudentTable
          students={students}
          duesMap={duesMap}
          duesLoading={duesLoading}
          activeAssignmentByStudent={activeAssignmentByStudent}
          bedLabelById={bedLabelById}
          onRefresh={fetchAll}
        />
      )}
    </div>
  )
}
