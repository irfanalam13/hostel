"use client";

import React, { useEffect, useState } from "react";
import { Button, EmptyState, useConfirm, useToast } from "@hostel/ui";
import { CheckCircle2, Flag, Trash2 } from "lucide-react";
import { Badge } from "@/features/platform/components/primitives";
import { moderationApi } from "../api/moderation.api";
import type { FlaggedReview } from "../types/moderation.types";

export function ModerationQueue() {
  const toast = useToast();
  const confirm = useConfirm();
  const [reviews, setReviews] = useState<FlaggedReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setReviews(await moderationApi.flagged());
    } catch (e) {
      toast.error((e as Error).message, "Failed to load flagged reviews");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const unflag = async (review: FlaggedReview) => {
    const yes = await confirm({
      message: `Restore this review by "${review.resident_name_snapshot}" to published?`,
      confirmText: "Restore",
    });
    if (!yes) return;
    setBusyId(review.id);
    try {
      await moderationApi.unflag(review.id);
      toast.success("Review restored to published.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (review: FlaggedReview) => {
    const yes = await confirm({
      title: "Remove review",
      message: `Permanently remove this review by "${review.resident_name_snapshot}"? This cannot be undone.`,
      danger: true,
      confirmText: "Remove",
    });
    if (!yes) return;
    setBusyId(review.id);
    try {
      await moderationApi.remove(review.id);
      toast.success("Review removed.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;

  if (reviews.length === 0) {
    return <EmptyState title="No flagged reviews" description="Nothing is waiting for a moderation decision." />;
  }

  return (
    <div className="space-y-3">
      {reviews.map((r) => (
        <div key={r.id} className="rounded-xl border border-[var(--border)] p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-[var(--foreground)]">{r.hostel_name}</span>
                <Badge color="var(--warning)">
                  <Flag className="h-3 w-3" /> {r.flag_count} flag{r.flag_count === 1 ? "" : "s"}
                </Badge>
                <Badge>{"★".repeat(r.rating)}</Badge>
              </div>
              <div className="mt-1 text-sm font-medium text-[var(--foreground-secondary)]">{r.title}</div>
              <p className="mt-1 max-w-2xl text-sm text-[var(--foreground-secondary)]">{r.body}</p>
              <div className="mt-2 text-xs text-[var(--muted)]">
                {r.resident_name_snapshot} · {r.verification_method} · {new Date(r.created_at).toLocaleDateString()}
              </div>
            </div>
            <div className="flex shrink-0 gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={busyId === r.id}
                onClick={() => unflag(r)}
              >
                <CheckCircle2 className="h-4 w-4" /> Restore
              </Button>
              <Button variant="ghost" size="sm" disabled={busyId === r.id} onClick={() => remove(r)}>
                <Trash2 className="h-4 w-4 text-[var(--error)]" /> Remove
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
