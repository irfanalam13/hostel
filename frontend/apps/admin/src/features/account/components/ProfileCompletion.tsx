"use client";

import type { AuthUser } from "@/features/auth/api/auth.api";
import { Card } from "@hostel/ui";
import { Check } from "lucide-react";
import { profileCompletion } from "../lib";

export function ProfileCompletion({ user }: { user: AuthUser | null }) {
  const { percent, items } = profileCompletion(user);
  const complete = percent === 100;

  return (
    <Card>
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
        {/* Progress ring */}
        <div className="relative grid h-24 w-24 shrink-0 place-items-center">
          <div
            className="h-24 w-24 rounded-full"
            style={{
              background: `conic-gradient(var(--accent) ${percent * 3.6}deg, var(--border) 0deg)`,
            }}
            aria-hidden
          />
          <div className="absolute grid h-[76px] w-[76px] place-items-center rounded-full bg-[var(--card)]">
            <span className="text-xl font-bold text-[var(--foreground)]">{percent}%</span>
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="text-base font-semibold text-[var(--foreground)]">
            {complete ? "Your profile is complete" : "Complete your profile"}
          </div>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            {complete
              ? "Nice work — everything we track today is filled in."
              : "A complete profile keeps your account recoverable and easy to recognise."}
          </p>

          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {items.map((item) => (
              <li key={item.key} className="flex items-center gap-2 text-sm">
                <span
                  className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${
                    item.done
                      ? "bg-[var(--success)] text-white"
                      : "border border-dashed border-[var(--border)] text-transparent"
                  }`}
                >
                  <Check className="h-3 w-3" />
                </span>
                <span
                  className={
                    item.done
                      ? "text-[var(--foreground-secondary)] line-through decoration-[var(--muted)]"
                      : "text-[var(--foreground)]"
                  }
                >
                  {item.label}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
