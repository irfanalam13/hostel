"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@hostel/ui";
import { Sparkles, X } from "lucide-react";
import { subscriptionApi, type PlanSummary } from "./api/subscription.api";

/**
 * Global upgrade experience (Module 12). Listens for the `entitlement:blocked`
 * window event that apiClient dispatches whenever a request is refused with
 * `feature_not_available` or `plan_limit_reached`, and shows an upgrade modal
 * naming the capability and the plans that unlock it — so a gated action never
 * dead-ends in a raw error.
 */

type BlockedDetail = {
  code: "feature_not_available" | "plan_limit_reached";
  detail?: string;
  feature?: string;
  feature_name?: string;
  limit?: string;
  limit_name?: string;
  current?: string | number;
  max?: string | number;
};

export function UpgradeProvider({ children }: { children: React.ReactNode }) {
  const [detail, setDetail] = useState<BlockedDetail | null>(null);
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const lastShown = useRef(0);

  const close = useCallback(() => setDetail(null), []);

  useEffect(() => {
    const handler = (e: Event) => {
      const d = (e as CustomEvent).detail as BlockedDetail;
      if (!d?.code) return;
      // Debounce a burst of identical blocks (e.g. several parallel requests).
      const now = Date.now();
      if (now - lastShown.current < 400) return;
      lastShown.current = now;

      setDetail(d);
      setPlans([]);
      setLoading(true);
      subscriptionApi
        .upgradeOptions(d.feature ? { feature: d.feature } : { limit: d.limit })
        .then((r) => setPlans(r.plans))
        .catch(() => setPlans([]))
        .finally(() => setLoading(false));
    };
    window.addEventListener("entitlement:blocked", handler);
    return () => window.removeEventListener("entitlement:blocked", handler);
  }, []);

  const isLimit = detail?.code === "plan_limit_reached";
  const title = isLimit
    ? "You've hit a plan limit"
    : `${detail?.feature_name || "This feature"} needs an upgrade`;

  return (
    <>
      {children}
      {detail ? (
        <div className="fixed inset-0 z-[95] flex items-center justify-center bg-black/50 p-3" onClick={close}>
          <div
            className="w-full max-w-lg overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card-elevated)] shadow-[var(--shadow-lg)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative bg-[var(--accent-soft)] px-6 py-5">
              <button onClick={close} aria-label="Close" className="absolute right-4 top-4 text-[var(--muted)] hover:text-[var(--foreground)]">
                <X className="h-5 w-5" />
              </button>
              <div className="flex items-center gap-2 text-[var(--accent)]">
                <Sparkles className="h-5 w-5" />
                <span className="text-xs font-semibold uppercase tracking-wide">Upgrade required</span>
              </div>
              <h2 className="mt-2 text-lg font-semibold text-[var(--foreground)]">{title}</h2>
              <p className="mt-1 text-sm text-[var(--foreground-secondary)]">
                {detail.detail ||
                  (isLimit
                    ? "Your current plan's quota is used up."
                    : "This capability isn't included in your current plan.")}
              </p>
              {isLimit && detail.max !== undefined ? (
                <p className="mt-1 text-xs text-[var(--muted)]">
                  Using {String(detail.current)} of {String(detail.max)} {detail.limit_name?.toLowerCase()}.
                </p>
              ) : null}
            </div>

            <div className="px-6 py-5">
              {loading ? (
                <div className="text-sm text-[var(--muted)]">Finding the right plan…</div>
              ) : plans.length > 0 ? (
                <>
                  <div className="mb-2 text-sm font-medium text-[var(--foreground)]">
                    Available in {plans.length === 1 ? "this plan" : "these plans"}:
                  </div>
                  <div className="space-y-2">
                    {plans.map((p) => (
                      <div
                        key={p.id}
                        className="flex items-center justify-between rounded-xl border border-[var(--border)] px-4 py-3"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-[var(--foreground)]">{p.name}</span>
                            {p.is_recommended ? (
                              <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-[11px] font-semibold text-[var(--accent)]">
                                Recommended
                              </span>
                            ) : null}
                          </div>
                          {p.description ? (
                            <div className="text-xs text-[var(--muted)]">{p.description}</div>
                          ) : null}
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-[var(--foreground)]">
                            {p.currency} {p.discounted_price}
                          </div>
                          <div className="text-[11px] text-[var(--muted)]">/ {p.billing_interval}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-sm text-[var(--muted)]">
                  Contact your account manager to enable this for your workspace.
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--border)] px-6 py-4">
              <Button variant="ghost" onClick={close}>
                Not now
              </Button>
              <Link href="/settings/billing" onClick={close}>
                <Button>Compare plans</Button>
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
