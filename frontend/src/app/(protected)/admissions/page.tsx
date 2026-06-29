"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  bulkApprove,
  bulkReject,
  exportAdmissionsExcel,
  getAnalytics,
  listAdmissions,
} from "@/features/admissions/api";
import type { AdmissionAnalytics, AdmissionRequest } from "@/features/admissions/types";
import { ADMISSION_STATUS_LABELS, SOURCE_OPTIONS } from "@/features/admissions/types";
import { AdmissionTable } from "@/features/admissions/components/AdmissionTable";
import { AdmissionDetailModal } from "@/features/admissions/components/AdmissionDetailModal";
import { AdmissionAnalytics as AnalyticsView } from "@/features/admissions/components/AdmissionAnalytics";
import { getBeds } from "@/features/beds/api/bed.api";
import type { Bed } from "@/features/beds/types/bed.types";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Select } from "@/shared/ui/Select";
import { Spinner } from "@/shared/ui/Spinner";
import { Topbar } from "@/shared/ui/Topbar";
import { useToast } from "@/shared/ui/toast/ToastProvider";

export default function AdmissionsPage() {
  const toast = useToast();
  const [tab, setTab] = useState<"list" | "analytics">("list");

  const [rows, setRows] = useState<AdmissionRequest[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [analytics, setAnalytics] = useState<AdmissionAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [active, setActive] = useState<AdmissionRequest | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [admissions, bedRows] = await Promise.all([
        listAdmissions({
          status: status || undefined,
          source: source || undefined,
          search: search || undefined,
          ordering: "-created_at",
        }),
        getBeds(),
      ]);
      setRows(admissions);
      setBeds(bedRows);
      setSelected(new Set());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load admissions.");
    } finally {
      setLoading(false);
    }
  }, [status, source, search, toast]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (tab === "analytics" && !analytics) {
      getAnalytics()
        .then(setAnalytics)
        .catch((err) => toast.error(err instanceof Error ? err.message : "Failed to load analytics."));
    }
  }, [tab, analytics, toast]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll(checked: boolean) {
    setSelected(checked ? new Set(rows.map((r) => r.id)) : new Set());
  }

  async function doBulk(kind: "approve" | "reject") {
    const ids = Array.from(selected);
    if (!ids.length) return toast.warning("Select at least one application.");
    try {
      if (kind === "approve") {
        const res = await bulkApprove(ids);
        toast.success(`Approved ${res.approved_count} application(s).`);
        if (res.errors?.length) toast.warning(res.errors[0]);
      } else {
        const res = await bulkReject(ids);
        toast.success(`Rejected ${res.rejected_count} application(s).`);
      }
      setAnalytics(null);
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Bulk action failed.");
    }
  }

  async function exportCsv() {
    try {
      await exportAdmissionsExcel();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed.");
    }
  }

  return (
    <div>
      <Topbar title="Admissions" />

      <div className="px-4 py-4 sm:px-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex gap-1 rounded-xl bg-[var(--background-secondary)] p-1 text-sm">
            {(["list", "analytics"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded-lg px-4 py-1.5 font-medium capitalize transition ${
                  tab === t ? "bg-[var(--accent)] text-white" : "text-[var(--foreground-secondary)]"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <Link href="/admissions/new">
            <Button>+ New Application</Button>
          </Link>
        </div>

        {tab === "list" && (
          <>
            <div className="mb-4 flex flex-wrap items-end gap-2">
              <div className="w-44">
                <Select
                  label="Status"
                  placeholder="All statuses"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  options={Object.entries(ADMISSION_STATUS_LABELS).map(([value, label]) => ({ value, label }))}
                />
              </div>
              <div className="w-40">
                <Select
                  label="Source"
                  placeholder="All sources"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  options={SOURCE_OPTIONS}
                />
              </div>
              <div className="w-56">
                <Input
                  label="Search"
                  placeholder="Name, phone, app no…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && refresh()}
                />
              </div>
              <Button variant="secondary" onClick={refresh}>
                Apply
              </Button>
              <div className="ml-auto flex gap-2">
                <Button variant="secondary" onClick={exportCsv}>
                  Export CSV
                </Button>
                <Button variant="secondary" disabled={!selected.size} onClick={() => doBulk("approve")}>
                  Approve ({selected.size})
                </Button>
                <Button variant="danger" disabled={!selected.size} onClick={() => doBulk("reject")}>
                  Reject ({selected.size})
                </Button>
              </div>
            </div>

            {loading ? (
              <div className="grid place-items-center py-16">
                <Spinner />
              </div>
            ) : (
              <AdmissionTable
                rows={rows}
                loading={loading}
                selected={selected}
                onToggle={toggle}
                onToggleAll={toggleAll}
                onOpen={setActive}
              />
            )}
          </>
        )}

        {tab === "analytics" &&
          (analytics ? (
            <AnalyticsView data={analytics} />
          ) : (
            <div className="grid place-items-center py-16">
              <Spinner />
            </div>
          ))}
      </div>

      {active && (
        <AdmissionDetailModal
          admission={active}
          beds={beds}
          onClose={() => setActive(null)}
          onChanged={() => {
            setAnalytics(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}
