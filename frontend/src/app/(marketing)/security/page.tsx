import type { Metadata } from "next";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { LegalDocument } from "@/features/landing/components/LegalDocument";
import { SECURITY_SECTIONS, LAST_UPDATED } from "@/features/landing/legal";

export const metadata: Metadata = {
  title: "Security",
  description: "How we keep your data safe — access control, encryption, auditing and recovery.",
  alternates: { canonical: "/security" },
};

export default function SecurityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Trust"
        title="Security"
        description="How we keep your data safe — access control, encryption, auditing and recovery."
        meta={LAST_UPDATED}
      />
      <LegalDocument sections={SECURITY_SECTIONS} />
    </>
  );
}
