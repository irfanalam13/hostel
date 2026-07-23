import type { Metadata } from "next";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { LegalDocument } from "@/features/landing/components/LegalDocument";
import { getLegalDocument } from "@/features/landing/site";

export const metadata: Metadata = {
  title: "Security",
  description: "How we keep your data safe — access control, encryption, auditing and recovery.",
  alternates: { canonical: "/security" },
};

export default async function SecurityPage() {
  const doc = await getLegalDocument("security");
  return (
    <>
      <PageHeader eyebrow={doc.eyebrow} title={doc.title} description={doc.description} meta={doc.last_updated} />
      <LegalDocument sections={doc.sections} />
    </>
  );
}
