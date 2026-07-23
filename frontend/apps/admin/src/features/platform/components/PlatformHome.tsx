"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@hostel/ui";
import { PLATFORM_SECTIONS } from "../registry";
import { platformApi } from "../api/platform.api";

export function PlatformHome() {
  const [stats, setStats] = useState({ plans: 0, activePlans: 0, features: 0, limits: 0 });

  useEffect(() => {
    Promise.all([
      platformApi.plans.list(),
      platformApi.features.list(),
      platformApi.limits.list(),
    ])
      .then(([plans, features, limits]) =>
        setStats({
          plans: plans.length,
          activePlans: plans.filter((p) => p.is_active && !p.is_archived).length,
          features: features.length,
          limits: limits.length,
        }),
      )
      .catch(() => {});
  }, []);

  const tiles = [
    { label: "Plans", value: stats.plans, sub: `${stats.activePlans} active` },
    { label: "Features", value: stats.features, sub: "in catalog" },
    { label: "Limits", value: stats.limits, sub: "definitions" },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5">
            <div className="text-sm text-[var(--muted)]">{t.label}</div>
            <div className="mt-1 text-3xl font-semibold text-[var(--foreground)]">{t.value}</div>
            <div className="text-xs text-[var(--muted)]">{t.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {PLATFORM_SECTIONS.filter((s) => s.id !== "home").map((s) => {
          const Icon = s.icon;
          return (
            <Link key={s.id} href={s.href}>
              <Card className="h-full">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="font-medium text-[var(--foreground)]">{s.label}</div>
                    <div className="text-sm text-[var(--muted)]">{s.description}</div>
                  </div>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
