import type { AdmissionStatus } from "../types";
import { ADMISSION_STATUS_LABELS } from "../types";

const STYLES: Record<AdmissionStatus, string> = {
  PENDING: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  UNDER_REVIEW: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  APPROVED: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  REJECTED: "bg-red-500/10 text-red-600 border-red-500/20",
  WAITLISTED: "bg-violet-500/10 text-violet-600 border-violet-500/20",
};

export function AdmissionStatusBadge({ status }: { status: AdmissionStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
        STYLES[status] || "bg-zinc-500/10 text-zinc-600 border-zinc-500/20"
      }`}
    >
      {ADMISSION_STATUS_LABELS[status] || status}
    </span>
  );
}
