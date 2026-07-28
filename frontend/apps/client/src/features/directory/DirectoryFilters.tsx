"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Input, Select } from "@hostel/ui";

const HOSTEL_TYPES = [
  { value: "boys", label: "Boys" },
  { value: "girls", label: "Girls" },
  { value: "co-ed", label: "Co-ed" },
  { value: "students", label: "Students" },
  { value: "workers", label: "Workers" },
];

const RATINGS = [
  { value: "4", label: "4+ stars" },
  { value: "3", label: "3+ stars" },
  { value: "2", label: "2+ stars" },
];

const SORTS = [
  { value: "", label: "Highest rated" },
  { value: "name", label: "Name (A-Z)" },
  { value: "-created_at", label: "Newest" },
];

/** Search/filter bar for the directory — every change updates the URL, so
 * the server component re-fetches with the new filters (bookmarkable,
 * back-button friendly). */
export function DirectoryFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();

  function update(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    params.delete("page");
    router.push(`/hostels${params.toString() ? `?${params.toString()}` : ""}`);
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Input
        placeholder="Search by name or city…"
        defaultValue={searchParams.get("search") ?? ""}
        onKeyDown={(e) => {
          if (e.key === "Enter") update("search", (e.target as HTMLInputElement).value);
        }}
        onBlur={(e) => update("search", e.target.value)}
      />
      <Select
        placeholder="Hostel type"
        value={searchParams.get("hostel_type") ?? ""}
        onChange={(e) => update("hostel_type", e.target.value)}
        options={HOSTEL_TYPES}
      />
      <Select
        placeholder="Minimum rating"
        value={searchParams.get("min_rating") ?? ""}
        onChange={(e) => update("min_rating", e.target.value)}
        options={RATINGS}
      />
      <Select
        value={searchParams.get("ordering") ?? ""}
        onChange={(e) => update("ordering", e.target.value)}
        options={SORTS}
      />
    </div>
  );
}
