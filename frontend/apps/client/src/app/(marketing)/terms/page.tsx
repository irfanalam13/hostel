import type { Metadata } from "next";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { LegalDocument } from "@/features/landing/components/LegalDocument";
import { getLegalDocument } from "@/features/landing/site";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms that govern your use of the platform.",
  alternates: { canonical: "/terms" },
};

export default async function TermsPage() {
  const doc = await getLegalDocument("terms");
  return (
    <>
      <PageHeader eyebrow={doc.eyebrow} title={doc.title} description={doc.description} meta={doc.last_updated} />
      <LegalDocument sections={doc.sections} />
    </>
  );
}
