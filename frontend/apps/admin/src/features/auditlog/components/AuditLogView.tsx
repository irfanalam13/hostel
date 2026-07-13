"use client";

import React from "react";
import { Button, Card, DataTable, Modal, Select, useToast, type Column } from "@hostel/ui";
import { useApi } from "@hostel/hooks";
import { usePermissions } from "@hostel/permissions";

import { auditApi } from "../api/audit.api";
import {
  AUDIT_ACTIONS,
  type AuditEvent,
  type AuditFilters,
  type AuditVerifyResult,
} from "../types/audit.types";

const RESULT_STYLES: Record<string, string> = {
  success: "bg-[color-mix(in_srgb,var(--success)_16%,transparent)] text-[var(--success)]",
  failure: "bg-[color-mix(in_srgb,var(--error)_16%,transparent)] text-[var(--error)]",
  denied: "bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] text-[var(--warning)]",
};

function ResultBadge({ result }: { result: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${RESULT_STYLES[result] ?? ""}`}>
      {result}
    </span>
  );
}

const PAGE_SIZE = 25;

export function AuditLogView() {
  const toast = useToast();
  const { can } = usePermissions();
  const isPlatformAdmin = can("platform:manage");

  const [filters, setFilters] = React.useState<AuditFilters>({ page: 1 });
  const [searchDraft, setSearchDraft] = React.useState("");
  const [selected, setSelected] = React.useState<AuditEvent | null>(null);
  const [verify, setVerify] = React.useState<AuditVerifyResult | null>(null);
  const [busy, setBusy] = React.useState(false);

  const { data, loading } = useApi(() => auditApi.list(filters), {
    deps: [JSON.stringify(filters)],
  });

  const rows = data?.results ?? [];
  const total = data?.count ?? 0;
  const page = filters.page ?? 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const patch = (next: Partial<AuditFilters>) =>
    setFilters((prev) => ({ ...prev, ...next, page: next.page ?? 1 }));

  const runExport = async () => {
    setBusy(true);
    try {
      await auditApi.exportCsv(filters);
    } catch {
      toast.error("Export failed.");
    } finally {
      setBusy(false);
    }
  };

  const runVerify = async () => {
    setBusy(true);
    try {
      const result = await auditApi.verify();
      setVerify(result);
      toast[result.ok ? "success" : "error"](
        result.ok ? `Chain intact — ${result.checked} events verified.` : "Integrity check FAILED.",
      );
    } catch {
      toast.error("Verification failed.");
    } finally {
      setBusy(false);
    }
  };

  const columns: Column<AuditEvent>[] = [
    {
      key: "created_at",
      header: "Time",
      sortable: true,
      render: (r) => new Date(r.created_at).toLocaleString(),
    },
    { key: "action", header: "Action", sortable: true },
    { key: "result", header: "Result", sortable: true, render: (r) => <ResultBadge result={r.result} /> },
    { key: "actor_label", header: "Actor", render: (r) => r.actor_label ?? "—" },
    {
      key: "entity",
      header: "Entity",
      accessor: (r) => `${r.entity_type} ${r.entity_id}`,
      render: (r) => (
        <span className="text-[var(--foreground-secondary)]">
          {r.entity_type || "—"}
          {r.entity_id ? `:${r.entity_id}` : ""}
        </span>
      ),
    },
    { key: "message", header: "Message" },
    {
      key: "status_code",
      header: "Status",
      align: "right",
      sortable: true,
      render: (r) => (r.status_code ?? "—"),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Audit trail</h1>
          <p className="text-sm text-[var(--foreground-secondary)]">
            Immutable, hash-chained record of privileged and security-relevant actions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={runExport} loading={busy}>
            Export CSV
          </Button>
          {isPlatformAdmin && (
            <Button variant="secondary" size="sm" onClick={runVerify} loading={busy}>
              Verify integrity
            </Button>
          )}
        </div>
      </div>

      {verify && (
        <Card
          className={`!p-3 text-sm ${
            verify.ok ? "text-[var(--success)]" : "text-[var(--error)]"
          }`}
        >
          {verify.ok
            ? `✓ Chain intact — ${verify.checked} events verified.`
            : `✗ Tampering detected at sequence ${verify.first_bad_sequence}: ${verify.reason}`}
          {!verify.ok && verify.errors.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-xs">
              {verify.errors.slice(0, 5).map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <Select
          label="Action"
          placeholder="All actions"
          value={filters.action ?? ""}
          onChange={(e) => patch({ action: e.target.value || undefined })}
          options={AUDIT_ACTIONS.map((a) => ({ value: a, label: a }))}
          className="min-w-[10rem]"
        />
        <Select
          label="Result"
          placeholder="All results"
          value={filters.result ?? ""}
          onChange={(e) => patch({ result: e.target.value || undefined })}
          options={[
            { value: "success", label: "Success" },
            { value: "failure", label: "Failure" },
            { value: "denied", label: "Denied" },
          ]}
          className="min-w-[9rem]"
        />
        <div>
          <div className="mb-1 text-sm text-[var(--foreground-secondary)]">Search</div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              patch({ search: searchDraft || undefined });
            }}
          >
            <input
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              placeholder="message, entity…"
              className="w-56 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
            />
          </form>
        </div>
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => String(r.id)}
        loading={loading}
        emptyMessage="No audit events match these filters."
        initialSort={{ key: "created_at", dir: "desc" }}
        onRowClick={(r) => setSelected(r)}
      />

      <div className="flex items-center justify-between text-sm text-[var(--foreground-secondary)]">
        <span>{total} event(s)</span>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onClick={() => patch({ page: page - 1 })}
          >
            Prev
          </Button>
          <span>
            {page} / {pageCount}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= pageCount}
            onClick={() => patch({ page: page + 1 })}
          >
            Next
          </Button>
        </div>
      </div>

      <Modal open={!!selected} title="Audit event" onClose={() => setSelected(null)}>
        {selected && (
          <div className="space-y-2 text-sm">
            <Field label="Sequence" value={String(selected.sequence ?? "—")} />
            <Field label="When" value={new Date(selected.created_at).toLocaleString()} />
            <Field label="Action" value={selected.action} />
            <Field label="Result" value={selected.result} />
            <Field label="Actor" value={selected.actor_label ?? "—"} />
            <Field label="Entity" value={`${selected.entity_type}:${selected.entity_id}`} />
            <Field label="Reason" value={selected.reason || "—"} />
            <Field label="IP" value={selected.ip_address ?? "—"} />
            <Field label="Request ID" value={selected.request_id || "—"} />
            {selected.changes && (
              <div>
                <div className="text-[var(--foreground-secondary)]">Changes</div>
                <pre className="max-h-40 overflow-auto rounded-lg bg-[var(--background-secondary)] p-2 text-xs">
                  {JSON.stringify(selected.changes, null, 2)}
                </pre>
              </div>
            )}
            <div>
              <div className="text-[var(--foreground-secondary)]">Content hash</div>
              <code className="block break-all text-xs">{selected.content_hash}</code>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[var(--foreground-secondary)]">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
