"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useToast } from "@hostel/ui";
import { NamespaceForm } from "@/features/workspace/components/NamespaceForm";
import { domainsApi, type CustomDomain, type DomainListing } from "../api/domains.api";

/**
 * Settings → Custom Domains (Prompt 05).
 *
 * Connect a domain → copy the DNS records (TXT ownership token or CNAME to
 * the workspace host) → verify → activate (becomes the primary public URL).
 * Status chips track verification, DNS health and SSL. White-label branding
 * lives below (schema-driven form over the `white_label` namespace).
 */

const card = "rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5";
const btn = "rounded-lg px-3 py-2 text-xs font-semibold transition disabled:opacity-50 ";
const btnPrimary = btn + "bg-[var(--accent)] text-white hover:opacity-90";
const btnGhost = btn + "border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--accent)]";
const btnDanger = btn + "border border-red-400/60 text-red-500 hover:bg-red-500/10";
const inputCls =
  "w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm " +
  "text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]";

const STATUS_TONE: Record<CustomDomain["status"], string> = {
  active: "bg-green-500/15 text-green-600",
  verified: "bg-blue-500/15 text-blue-600",
  pending: "bg-amber-500/15 text-amber-600",
  failed: "bg-red-500/15 text-red-500",
  disabled: "bg-gray-500/15 text-[var(--muted)]",
};

const SSL_TONE: Record<CustomDomain["ssl_status"], string> = {
  active: "text-green-600",
  expiring: "text-amber-600",
  expired: "text-red-500",
  pending: "text-[var(--muted)]",
  unknown: "text-[var(--muted)]",
  error: "text-red-500",
};

function Chip({ label, tone }: { label: string; tone: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${tone}`}>
      {label}
    </span>
  );
}

function RecordRow({ record, onCopy }: { record: { type: string; host: string; value: string }; onCopy: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] p-2 font-mono text-xs">
      <span className="rounded bg-[var(--accent)]/10 px-1.5 py-0.5 font-bold text-[var(--accent)]">
        {record.type}
      </span>
      <span className="break-all text-[var(--muted)]">{record.host}</span>
      <span className="text-[var(--muted)]">→</span>
      <span className="break-all text-[var(--foreground)]">{record.value}</span>
      <button type="button" onClick={onCopy}
              className="ml-auto text-[10px] font-semibold text-[var(--accent)] hover:underline">
        Copy value
      </button>
    </div>
  );
}

export function CustomDomainsSection() {
  const toast = useToast();
  const [listing, setListing] = useState<DomainListing | null>(null);
  const [newDomain, setNewDomain] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setListing(await domainsApi.list());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load domains.");
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function run(key: string, action: () => Promise<unknown>, success?: string) {
    if (busy) return;
    setBusy(key);
    try {
      await action();
      if (success) toast.success(success);
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Action failed", "Error");
    } finally {
      setBusy(null);
    }
  }

  function copy(value: string) {
    void navigator.clipboard?.writeText(value).then(() => toast.success("Copied."));
  }

  if (error) return <div className={card}><p className="text-sm text-red-500">{error}</p></div>;
  if (!listing) return <div className={card}><p className="text-sm text-[var(--muted)]">Loading…</p></div>;

  const canAdd = listing.domains.length < listing.limit;

  return (
    <div className="space-y-4">
      <div className={card}>
        <h3 className="text-sm font-bold text-[var(--foreground)]">Custom domains</h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          Replace your workspace URL with your own branded domain. Your default URL keeps working —
          the public site permanently redirects to the primary domain.
        </p>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <div>
            <span className="text-[var(--muted)]">Workspace URL: </span>
            <span className="font-mono text-[var(--foreground)]">{listing.workspace_url}</span>
          </div>
          <div>
            <span className="text-[var(--muted)]">Public URL: </span>
            <a href={listing.public_url} target="_blank" rel="noopener noreferrer"
               className="font-mono text-[var(--accent)] hover:underline">{listing.public_url}</a>
          </div>
          <div>
            <span className="text-[var(--muted)]">Plan allowance: </span>
            <span className="font-semibold text-[var(--foreground)]">
              {listing.domains.length}/{listing.limit}
            </span>
          </div>
        </div>

        <div className="mt-4 flex max-w-md gap-2">
          <input className={inputCls} placeholder="hostel.yourdomain.com"
                 value={newDomain} onChange={(e) => setNewDomain(e.target.value.toLowerCase())} />
          <button
            className={btnPrimary}
            disabled={!newDomain.trim() || !canAdd || busy !== null}
            onClick={() => run("add", async () => {
              await domainsApi.add(newDomain.trim());
              setNewDomain("");
            }, "Domain added — now add the DNS records below and verify.")}
          >
            Connect domain
          </button>
        </div>
        {!canAdd && (
          <p className="mt-2 text-xs text-amber-600">
            Your plan allows {listing.limit} custom domain{listing.limit === 1 ? "" : "s"}. Upgrade to connect more.
          </p>
        )}
      </div>

      {listing.domains.map((d) => (
        <div key={d.id} className={card}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm font-bold text-[var(--foreground)]">{d.domain}</span>
              <Chip label={d.status} tone={STATUS_TONE[d.status]} />
              {d.is_primary && <Chip label="primary" tone="bg-[var(--accent)]/15 text-[var(--accent)]" />}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(d.status === "pending" || d.status === "failed") && (
                <button className={btnPrimary} disabled={busy !== null}
                        onClick={() => run(d.id, () => domainsApi.verify(d.id))}>
                  {busy === d.id ? "Checking DNS…" : "Verify now"}
                </button>
              )}
              {d.status === "verified" && (
                <button className={btnPrimary} disabled={busy !== null}
                        onClick={() => run(d.id, () => domainsApi.activate(d.id),
                                           "Domain activated — it is now your primary public URL.")}>
                  Activate
                </button>
              )}
              {d.status === "active" && !d.is_primary && (
                <button className={btnGhost} disabled={busy !== null}
                        onClick={() => run(d.id, () => domainsApi.setPrimary(d.id), "Primary domain updated.")}>
                  Make primary
                </button>
              )}
              {d.status === "active" && (
                <>
                  <button className={btnGhost} disabled={busy !== null}
                          onClick={() => run(d.id, () => domainsApi.checkSsl(d.id))}>
                    Check SSL
                  </button>
                  <button className={btnGhost} disabled={busy !== null}
                          onClick={() => run(d.id, () => domainsApi.disable(d.id), "Domain disabled.")}>
                    Disable
                  </button>
                </>
              )}
              {d.status === "disabled" && (
                <button className={btnGhost} disabled={busy !== null}
                        onClick={() => run(d.id, () => domainsApi.activate(d.id), "Domain re-activated.")}>
                  Re-activate
                </button>
              )}
              <button className={btnDanger} disabled={busy !== null}
                      onClick={() => {
                        if (window.confirm(`Remove ${d.domain}? It will stop routing to your workspace.`)) {
                          void run(d.id, () => domainsApi.remove(d.id), "Domain removed.");
                        }
                      }}>
                Remove
              </button>
            </div>
          </div>

          {/* Health row */}
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--muted)]">
            <span>DNS: TXT {d.dns_health?.txt ? "✅" : "—"} · CNAME {d.dns_health?.cname ? "✅" : "—"}</span>
            <span className={SSL_TONE[d.ssl_status]}>
              SSL: {d.ssl_status}
              {d.ssl_expires_at ? ` (expires ${new Date(d.ssl_expires_at).toLocaleDateString()})` : ""}
            </span>
            {d.last_checked_at && <span>Last check: {new Date(d.last_checked_at).toLocaleString()}</span>}
          </div>
          {d.last_error && d.status !== "active" && (
            <p className="mt-2 text-xs text-amber-600">{d.last_error}</p>
          )}

          {/* DNS instructions until active */}
          {d.status !== "active" && d.status !== "disabled" && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-[var(--muted)]">
                Add <strong>either</strong> record at your DNS provider, then click “Verify now”
                (propagation can take up to 48 hours — we also retry automatically):
              </p>
              <RecordRow record={d.records.txt} onCopy={() => copy(d.records.txt.value)} />
              <RecordRow record={d.records.cname} onCopy={() => copy(d.records.cname.value)} />
            </div>
          )}
        </div>
      ))}

      {/* White-label branding — schema-driven over the white_label namespace. */}
      <NamespaceForm
        namespace="white_label"
        title="White-label branding"
        description="Present the platform as your hostel's own system: platform name, browser title, email sender name, footer text — and hide platform branding entirely."
      />
    </div>
  );
}
