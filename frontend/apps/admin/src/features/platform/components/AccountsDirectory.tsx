"use client";

import React, { useEffect, useState } from "react";
import { EmptyState, Input, Table, useToast } from "@hostel/ui";
import { platformApi } from "../api/platform.api";
import type { PlatformAccount } from "../types/platform.types";
import { Badge } from "./primitives";

const PAGE_SIZE = 50;

export function AccountsDirectory() {
  const toast = useToast();
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = async (nextOffset: number, nextSearch: string) => {
    setLoading(true);
    try {
      const page = await platformApi.accounts.list({
        search: nextSearch || undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });
      setAccounts((prev) => (nextOffset === 0 ? page.accounts : [...prev, ...page.accounts]));
      setCount(page.count);
    } catch (e) {
      toast.error((e as Error).message, "Failed to load accounts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => {
      setOffset(0);
      load(0, search);
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const loadMore = () => {
    const next = offset + PAGE_SIZE;
    setOffset(next);
    load(next, search);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Input
          placeholder="Search by username, email or name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <div className="text-xs text-[var(--muted)]">{count} account{count === 1 ? "" : "s"}</div>
      </div>

      {!loading && accounts.length === 0 ? (
        <EmptyState title="No accounts found" description="Try a different search term." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Account</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Hostels &amp; plan</th>
              <th className="px-4 py-3 font-medium">Last login</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id} className="border-b border-[var(--border)] last:border-0 align-top">
                <td className="px-4 py-2.5">
                  <div className="font-medium text-[var(--foreground)]">{a.full_name || a.username}</div>
                  <div className="text-xs text-[var(--muted)]">{a.email || a.username}</div>
                </td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{a.role}</td>
                <td className="px-4 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {a.is_superuser ? <Badge tone="accent">superadmin</Badge> : null}
                    <Badge tone={a.is_active ? "neutral" : "warning"} color={a.is_active ? undefined : "var(--error)"}>
                      {a.is_active ? "active" : "disabled"}
                    </Badge>
                  </div>
                </td>
                <td className="px-4 py-2.5">
                  {a.memberships.length === 0 ? (
                    <span className="text-xs text-[var(--muted)]">No hostel</span>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {a.memberships.map((m) => (
                        <Badge key={m.hostel_id}>
                          {m.hostel_name} · {m.plan_name || "no plan"}
                        </Badge>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-4 py-2.5 text-[var(--muted)]">
                  {a.last_login ? new Date(a.last_login).toLocaleString() : "Never"}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {accounts.length < count ? (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={loadMore}
            disabled={loading}
            className="rounded-lg border border-[var(--border)] px-4 py-1.5 text-sm text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)] disabled:opacity-50"
          >
            {loading ? "Loading…" : "Load more"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
