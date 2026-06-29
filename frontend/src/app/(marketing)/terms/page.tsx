import type { Metadata } from "next";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { LegalDocument } from "@/features/landing/components/LegalDocument";
import { TERMS_SECTIONS, LAST_UPDATED } from "@/features/landing/legal";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms that govern your use of the platform.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Legal"
        title="Terms of Service"
        description="The terms that govern your use of the platform."
        meta={LAST_UPDATED}
      />
      <LegalDocument sections={TERMS_SECTIONS} />
    </>
  );
}
