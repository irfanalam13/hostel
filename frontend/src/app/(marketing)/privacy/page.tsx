import type { Metadata } from "next";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { LegalDocument } from "@/features/landing/components/LegalDocument";
import { PRIVACY_SECTIONS, LAST_UPDATED } from "@/features/landing/legal";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How we collect, use, and protect your information.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Legal"
        title="Privacy Policy"
        description="How we collect, use, and protect your information."
        meta={LAST_UPDATED}
      />
      <LegalDocument sections={PRIVACY_SECTIONS} />
    </>
  );
}
