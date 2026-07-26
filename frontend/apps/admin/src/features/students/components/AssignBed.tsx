"use client";

import { useEffect, useMemo, useState } from "react";
import type { Bed } from "@/features/beds/api/bed.api";
import {
  createBedAssignment,
  endBedAssignment,
  getActiveAssignmentByBed,
  getActiveAssignmentByStudent,
  getBeds,
} from "@/features/beds/api/bed.api";

function todayYYYYMMDD() {
  return new Date().toISOString().slice(0, 10);
}

export default function AssignBed({ studentId }: { studentId: string }) {
  const [beds, setBeds] = useState<Bed[]>([]);
  const [active, setActive] = useState<{ id: string; bed: string } | null>(null);
  const [selectedBed, setSelectedBed] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    setErr("");
    getBeds({ status: "AVAILABLE", ordering: "bed_no" })
      .then((data) => mounted && setBeds(Array.isArray(data) ? data : []))
      .catch((e) => mounted && setErr(e?.message || "Failed to load beds"));
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    setErr("");
    getActiveAssignmentByStudent(studentId)
      .then((assignment) =>
        mounted && setActive(assignment ? { id: assignment.id, bed: assignment.bed } : null)
      )
      .catch((e) => mounted && setErr(e?.message || "Failed to load current assignment"));
    return () => {
      mounted = false;
    };
  }, [studentId]);

  const bedMap = useMemo(() => {
    const map = new Map<string, Bed>();
    beds.forEach((bed) => map.set(bed.id, bed));
    return map;
  }, [beds]);

  const currentBedLabel = active?.bed ? bedMap.get(active.bed)?.code ?? `#${active.bed}` : "-";

  const assignOrSwitch = async () => {
    if (selectedBed === "") return;

    const bedId = selectedBed;
    setLoading(true);
    setErr("");

    try {
      const bedActive = await getActiveAssignmentByBed(bedId);
      if (bedActive && bedActive.student !== studentId) {
        setErr("This bed is already occupied. Choose another bed.");
        return;
      }

      if (active) {
        await endBedAssignment(active.id, { is_active: false, end_date: todayYYYYMMDD() });
      }

      const next = await createBedAssignment({
        student: studentId,
        bed: bedId,
        start_date: todayYYYYMMDD(),
        is_active: true,
      });

      setActive({ id: next.id, bed: next.bed });
      setSelectedBed("");
    } catch (e: any) {
      setErr(e?.message || "Failed to assign bed");
    } finally {
      setLoading(false);
    }
  };

  const unassign = async () => {
    if (!active) return;

    setLoading(true);
    setErr("");
    try {
      await endBedAssignment(active.id, { is_active: false, end_date: todayYYYYMMDD() });
      setActive(null);
    } catch (e: any) {
      setErr(e?.message || "Failed to unassign bed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border rounded p-4 mt-4 bg-white">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="font-semibold">Bed Assignment</div>
        <div className="text-sm">
          Current bed: <span className="font-semibold">{currentBedLabel}</span>
        </div>
      </div>

      {err ? (
        <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {err}
        </div>
      ) : null}

      <div className="flex flex-col md:flex-row gap-2">
        <select
          className="border p-2 rounded w-full md:w-96"
          value={selectedBed}
          onChange={(e) => setSelectedBed(e.target.value)}
          disabled={loading}
        >
          <option value="">Select a bed</option>
          {beds.map((bed) => (
            <option key={bed.id} value={bed.id}>
              {bed.code ?? `Room ${bed.room} / Bed ${bed.bed_no}`}
            </option>
          ))}
        </select>

        <button
          className="border px-3 py-2 rounded disabled:opacity-60"
          onClick={assignOrSwitch}
          disabled={loading || selectedBed === ""}
        >
          {loading ? "Saving..." : active ? "Switch Bed" : "Assign"}
        </button>

        <button
          className="border px-3 py-2 rounded disabled:opacity-60"
          onClick={unassign}
          disabled={loading || !active}
        >
          Unassign
        </button>
      </div>
    </div>
  );
}
