import type { Metadata } from "next";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { LegalDocument } from "@/features/landing/components/LegalDocument";
import { getLegalDocument } from "@/features/landing/site";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How we collect, use, and protect your information.",
  alternates: { canonical: "/privacy" },
};

export default async function PrivacyPage() {
  const doc = await getLegalDocument("privacy");
  return (
    <>
      <PageHeader eyebrow={doc.eyebrow} title={doc.title} description={doc.description} meta={doc.last_updated} />
      <LegalDocument sections={doc.sections} />
    </>
  );
}
