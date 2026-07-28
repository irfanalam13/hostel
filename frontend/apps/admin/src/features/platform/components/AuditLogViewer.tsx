"use client";

import React, { useEffect, useState } from "react";
import { apiDownload } from "@hostel/api";
import { Button, EmptyState, Input, Modal, Select, Table, useToast } from "@hostel/ui";
import { Download, ShieldCheck } from "lucide-react";
import { platformApi } from "../api/platform.api";
import { AUDIT_ACTIONS } from "@/features/auditlog/types/audit.types";
import type { AuditEvent } from "../types/platform.types";
import { Badge } from "./primitives";

const RESULT_TONE: Record<string, string | undefined> = {
  success: "var(--success)",
  failure: "var(--error)",
  denied: "var(--warning)",
};

export function AuditLogViewer() {
  const toast = useToast();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [result, setResult] = useState("");
  const [verifyResult, setVerifyResult] = useState<{ ok: boolean; checked: number; first_bad_sequence: number | null; reason: string } | null>(null);

  const filters = () => ({
    search: search || undefined,
    action: action || undefined,
    result: result || undefined,
  });

  const load = async () => {
    setLoading(true);
    try {
      setEvents(await platformApi.audit.list(filters()));
    } catch (e) {
      toast.error((e as Error).message, "Failed to load audit events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, action, result]);

  const runExport = async () => {
    setBusy(true);
    try {
      const qs = new URLSearchParams(
        Object.entries(filters()).filter(([, v]) => v !== undefined) as [string, string][],
      ).toString();
      await apiDownload(`/platform/audit/events/export/${qs ? `?${qs}` : ""}`, "platform-audit-events.csv");
    } catch (e) {
      toast.error((e as Error).message, "Export failed");
    } finally {
      setBusy(false);
    }
  };

  const runVerify = async () => {
    setBusy(true);
    try {
      const r = await platformApi.audit.verifyChain();
      setVerifyResult(r);
      toast[r.ok ? "success" : "error"](
        r.ok ? `Chain intact — ${r.checked} events verified.` : `Tampering detected at sequence ${r.first_bad_sequence}.`,
      );
    } catch (e) {
      toast.error((e as Error).message, "Verification failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-2">
          <Input
            label="Search"
            placeholder="message, entity…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="min-w-[14rem]"
          />
          <Select
            label="Action"
            placeholder="All actions"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            options={AUDIT_ACTIONS.map((a) => ({ value: a, label: a }))}
            className="min-w-[10rem]"
          />
          <Select
            label="Result"
            placeholder="All results"
            value={result}
            onChange={(e) => setResult(e.target.value)}
            options={[
              { value: "success", label: "Success" },
              { value: "failure", label: "Failure" },
              { value: "denied", label: "Denied" },
            ]}
            className="min-w-[9rem]"
          />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" loading={busy} onClick={runExport}>
            <Download className="h-4 w-4" /> Export CSV
          </Button>
          <Button variant="secondary" size="sm" loading={busy} onClick={runVerify}>
            <ShieldCheck className="h-4 w-4" /> Verify chain
          </Button>
        </div>
      </div>

      {verifyResult ? (
        <div className={`rounded-lg border p-3 text-sm ${verifyResult.ok ? "border-[var(--success)] text-[var(--success)]" : "border-[var(--error)] text-[var(--error)]"}`}>
          {verifyResult.ok
            ? `Chain intact — ${verifyResult.checked} events verified.`
            : `Tampering detected at sequence ${verifyResult.first_bad_sequence}: ${verifyResult.reason}`}
        </div>
      ) : null}

      {!loading && events.length === 0 ? (
        <EmptyState title="No audit events" description="Nothing matches these filters." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Result</th>
              <th className="px-4 py-3 font-medium">Actor</th>
              <th className="px-4 py-3 font-medium">Entity</th>
              <th className="px-4 py-3 font-medium">Message</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr
                key={e.id}
                className="cursor-pointer border-b border-[var(--border)] last:border-0 hover:bg-[var(--background-secondary)]"
                onClick={() => setSelected(e)}
              >
                <td className="px-4 py-2.5 text-[var(--muted)]">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-4 py-2.5 text-[var(--foreground)]">{e.action}</td>
                <td className="px-4 py-2.5">
                  <Badge color={RESULT_TONE[e.result]}>{e.result}</Badge>
                </td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{e.actor_label ?? "—"}</td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">
                  {e.entity_type || "—"}
                  {e.entity_id ? `:${e.entity_id}` : ""}
                </td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{e.message}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={!!selected} title="Audit event" onClose={() => setSelected(null)}>
        {selected ? (
          <div className="space-y-2 text-sm">
            <DetailRow label="Sequence" value={String(selected.sequence ?? "—")} />
            <DetailRow label="When" value={new Date(selected.created_at).toLocaleString()} />
            <DetailRow label="Action" value={selected.action} />
            <DetailRow label="Result" value={selected.result} />
            <DetailRow label="Actor" value={selected.actor_label ?? "—"} />
            <DetailRow label="Entity" value={`${selected.entity_type}:${selected.entity_id}`} />
            <DetailRow label="Reason" value={selected.reason || "—"} />
            <DetailRow label="IP" value={selected.ip_address ?? "—"} />
            <DetailRow label="Request ID" value={selected.request_id || "—"} />
            {selected.changes ? (
              <div>
                <div className="text-[var(--foreground-secondary)]">Changes</div>
                <pre className="max-h-40 overflow-auto rounded-lg bg-[var(--background-secondary)] p-2 text-xs">
                  {JSON.stringify(selected.changes, null, 2)}
                </pre>
              </div>
            ) : null}
            {Object.keys(selected.meta || {}).length > 0 ? (
              <div>
                <div className="text-[var(--foreground-secondary)]">Meta</div>
                <pre className="max-h-40 overflow-auto rounded-lg bg-[var(--background-secondary)] p-2 text-xs">
                  {JSON.stringify(selected.meta, null, 2)}
                </pre>
              </div>
            ) : null}
            <div>
              <div className="text-[var(--foreground-secondary)]">Content hash</div>
              <code className="block break-all text-xs">{selected.content_hash}</code>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[var(--foreground-secondary)]">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
