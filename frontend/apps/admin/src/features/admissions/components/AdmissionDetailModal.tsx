"use client";

import React, { useRef, useState } from "react";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Select } from "@hostel/ui";
import { Textarea } from "@hostel/ui";
import { useToast } from "@hostel/ui";
import type { Bed } from "@/features/beds/types/bed.types";
import {
  approveAdmission,
  downloadAdmissionPdf,
  rejectAdmission,
  uploadDocument,
} from "../api";
import type { AdmissionDocType, AdmissionRequest } from "../types";
import { DOC_TYPE_OPTIONS, PAYMENT_STATUS_OPTIONS } from "../types";
import { AdmissionStatusBadge } from "./AdmissionStatusBadge";

const DECISIONABLE = ["PENDING", "UNDER_REVIEW"];

function Row({ label, value }: { label: string; value?: React.ReactNode }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="flex justify-between gap-3 border-b border-[var(--border)] py-1.5 text-sm">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="text-right font-medium text-[var(--foreground)]">{value}</span>
    </div>
  );
}

export function AdmissionDetailModal({
  admission,
  beds,
  onClose,
  onChanged,
}: {
  admission: AdmissionRequest;
  beds: Bed[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState<"details" | "documents" | "decision">("details");
  const [busy, setBusy] = useState(false);

  const [docType, setDocType] = useState<AdmissionDocType>("passport_photo");
  const [decision, setDecision] = useState({
    bed: admission.preferred_bed || "",
    join_date: admission.booking_date || new Date().toISOString().slice(0, 10),
    decision_note: "",
    monthly_fee: String(admission.monthly_fee || ""),
    security_deposit: String(admission.security_deposit || ""),
    admission_fee: String(admission.admission_fee || ""),
    discount: String(admission.discount || ""),
    scholarship: String(admission.scholarship || ""),
    receipt_number: admission.receipt_number || "",
    payment_status: admission.payment_status || "PENDING",
  });
  const [rejectReason, setRejectReason] = useState("");

  const availableBeds = beds.filter((b) => b.status === "AVAILABLE");
  const canDecide = DECISIONABLE.includes(admission.status);

  async function handleApprove() {
    setBusy(true);
    try {
      await approveAdmission(admission.id, {
        bed: decision.bed || undefined,
        join_date: decision.join_date || undefined,
        decision_note: decision.decision_note,
        monthly_fee: decision.monthly_fee ? Number(decision.monthly_fee) : undefined,
        security_deposit: decision.security_deposit ? Number(decision.security_deposit) : undefined,
        admission_fee: decision.admission_fee ? Number(decision.admission_fee) : undefined,
        discount: decision.discount ? Number(decision.discount) : undefined,
        scholarship: decision.scholarship ? Number(decision.scholarship) : undefined,
        receipt_number: decision.receipt_number || undefined,
        payment_status: decision.payment_status as never,
      });
      toast.success("Admission approved — student record & login created.");
      onChanged();
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Approval failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleReject() {
    setBusy(true);
    try {
      await rejectAdmission(admission.id, "Rejected from admissions screen.", rejectReason);
      toast.success("Application rejected.");
      onChanged();
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Rejection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(file: File) {
    setBusy(true);
    try {
      await uploadDocument(admission.id, docType, file);
      toast.success("Document uploaded.");
      onChanged();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-3" onClick={onClose}>
      <div
        className="my-6 w-full max-w-2xl rounded-3xl border border-[var(--border)] bg-[var(--card-elevated)] p-5 shadow-[var(--shadow-lg)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold">{admission.full_name}</h2>
              <AdmissionStatusBadge status={admission.status} />
            </div>
            <div className="font-mono text-xs text-[var(--muted)]">{admission.application_number}</div>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => downloadAdmissionPdf(admission.id, admission.application_number)}
            >
              PDF
            </Button>
            <Button size="sm" variant="ghost" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>

        <div className="mb-4 flex gap-1 rounded-xl bg-[var(--background-secondary)] p-1 text-sm">
          {(["details", "documents", "decision"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 rounded-lg px-3 py-1.5 font-medium capitalize transition ${
                tab === t ? "bg-[var(--accent)] text-white" : "text-[var(--foreground-secondary)]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "details" && (
          <div className="space-y-1">
            <Row label="Phone" value={admission.phone} />
            <Row label="Alt. phone" value={admission.alternate_phone} />
            <Row label="Email" value={admission.email} />
            <Row label="Gender" value={admission.gender} />
            <Row label="Date of birth" value={admission.date_of_birth} />
            <Row label="Citizenship no." value={admission.citizenship_number} />
            <Row
              label="Permanent address"
              value={[admission.street_tole, admission.municipality, admission.district, admission.province]
                .filter(Boolean)
                .join(", ")}
            />
            <Row label="Institute" value={admission.educational_institute} />
            <Row label="Level / Faculty" value={[admission.current_level, admission.faculty].filter(Boolean).join(" · ")} />
            <Row label="Food preference" value={admission.food_preference} />
            <Row label="Father" value={[admission.father_name, admission.father_phone].filter(Boolean).join(" · ")} />
            <Row label="Mother" value={[admission.mother_name, admission.mother_phone].filter(Boolean).join(" · ")} />
            <Row
              label="Local guardian"
              value={[admission.local_guardian_name, admission.local_guardian_phone].filter(Boolean).join(" · ")}
            />
            <Row label="Preferred room type" value={admission.preferred_room_type} />
            <Row label="Assigned bed" value={admission.approved_bed_code} />
            <Row label="Payment status" value={admission.payment_status} />
            {admission.status === "REJECTED" && <Row label="Rejection reason" value={admission.rejection_reason} />}
          </div>
        )}

        {tab === "documents" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto] sm:items-end">
              <Select
                label="Document type"
                options={DOC_TYPE_OPTIONS}
                value={docType}
                onChange={(e) => setDocType(e.target.value as AdmissionDocType)}
              />
              <div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
                />
                <Button variant="secondary" disabled={busy} onClick={() => fileRef.current?.click()}>
                  Upload file
                </Button>
              </div>
            </div>
            <p className="text-xs text-[var(--muted)]">Allowed: PDF, PNG, JPG, JPEG.</p>
            <div className="divide-y divide-[var(--border)] rounded-xl border border-[var(--border)]">
              {admission.documents.length === 0 ? (
                <div className="p-4 text-center text-sm text-[var(--muted)]">No documents uploaded.</div>
              ) : (
                admission.documents.map((d) => (
                  <div key={d.id} className="flex items-center justify-between p-3 text-sm">
                    <span className="capitalize">{d.doc_type.replace(/_/g, " ")}</span>
                    <a
                      href={d.file}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-[var(--accent)] hover:underline"
                    >
                      View
                    </a>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {tab === "decision" && (
          <div className="space-y-4">
            {!canDecide ? (
              <div className="rounded-xl bg-[var(--background-secondary)] p-4 text-sm text-[var(--muted)]">
                This application is <strong>{admission.status}</strong> and can no longer be decided.
                {admission.student_name ? ` Student: ${admission.student_name}.` : ""}
              </div>
            ) : (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select
                    label="Assign bed"
                    placeholder="No bed"
                    value={decision.bed}
                    onChange={(e) => setDecision({ ...decision, bed: e.target.value })}
                  >
                    {availableBeds.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.code || `${b.room_detail?.room_no || b.room}-${b.bed_no}`}
                      </option>
                    ))}
                  </Select>
                  <Input
                    label="Join date"
                    type="date"
                    value={decision.join_date}
                    onChange={(e) => setDecision({ ...decision, join_date: e.target.value })}
                  />
                  <Input
                    label="Monthly fee"
                    type="number"
                    value={decision.monthly_fee}
                    onChange={(e) => setDecision({ ...decision, monthly_fee: e.target.value })}
                  />
                  <Input
                    label="Security deposit"
                    type="number"
                    value={decision.security_deposit}
                    onChange={(e) => setDecision({ ...decision, security_deposit: e.target.value })}
                  />
                  <Input
                    label="Admission fee"
                    type="number"
                    value={decision.admission_fee}
                    onChange={(e) => setDecision({ ...decision, admission_fee: e.target.value })}
                  />
                  <Input
                    label="Discount"
                    type="number"
                    value={decision.discount}
                    onChange={(e) => setDecision({ ...decision, discount: e.target.value })}
                  />
                  <Input
                    label="Receipt number"
                    value={decision.receipt_number}
                    onChange={(e) => setDecision({ ...decision, receipt_number: e.target.value })}
                  />
                  <Select
                    label="Payment status"
                    options={PAYMENT_STATUS_OPTIONS}
                    value={decision.payment_status}
                    onChange={(e) => setDecision({ ...decision, payment_status: e.target.value as never })}
                  />
                </div>
                <Textarea
                  label="Decision note"
                  value={decision.decision_note}
                  onChange={(e) => setDecision({ ...decision, decision_note: e.target.value })}
                />
                <Button className="w-full" loading={busy} onClick={handleApprove}>
                  Approve & create student
                </Button>

                <div className="rounded-xl border border-[var(--border)] p-3">
                  <Textarea
                    label="Rejection reason"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                  />
                  <Button variant="danger" className="mt-2 w-full" loading={busy} onClick={handleReject}>
                    Reject application
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
