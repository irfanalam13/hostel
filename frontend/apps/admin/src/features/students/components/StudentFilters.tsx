"use client"

export default function StudentFilters({
  search,
  status,
  onChange,
}: {
  search: string
  status: "" | "ACTIVE" | "INACTIVE"
  onChange: (next: { search: string; status: "" | "ACTIVE" | "INACTIVE" }) => void
}) {
  return (
    <div className="flex flex-col md:flex-row gap-3 mb-4">
      <input
        className="border p-2 rounded w-full md:w-80"
        placeholder="Search: name / phone / guardian phone"
        value={search}
        onChange={(e) => onChange({ search: e.target.value, status })}
      />

      <select
        className="border p-2 rounded w-full md:w-56"
        value={status}
        onChange={(e) => onChange({ search, status: e.target.value as any })}
      >
        <option value="">All status</option>
        <option value="ACTIVE">ACTIVE</option>
        <option value="INACTIVE">INACTIVE</option>
      </select>
    </div>
  )
}