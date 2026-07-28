import type { Metadata } from "next";
import { PageHeader } from "@/features/landing/components/PageHeader";
import { Section } from "@/features/landing/components/Section";
import { BRAND } from "@/features/landing/content";
import { listDirectoryHostels } from "@/features/directory/api";
import { DirectoryFilters } from "@/features/directory/DirectoryFilters";
import { HostelGrid } from "@/features/directory/HostelGrid";
import { buildDirectoryJsonLd } from "@/features/directory/seo";

export const metadata: Metadata = {
  title: "Find a hostel",
  description: `Browse and compare hostels on ${BRAND.name} — filter by type and rating, and read reviews from verified residents.`,
  alternates: { canonical: "/hostels" },
};

type SearchParams = {
  search?: string;
  hostel_type?: string;
  min_rating?: string;
  ordering?: string;
};

export default async function HostelsDirectoryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const page = await listDirectoryHostels({
    search: params.search,
    hostel_type: params.hostel_type,
    min_rating: params.min_rating ? Number(params.min_rating) : undefined,
    ordering: params.ordering,
  });

  return (
    <>
      <script
        type="application/ld+json"
        // Directory listing structured data; content is our own backend, safely serialized.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(buildDirectoryJsonLd(page.items)) }}
      />
      <PageHeader
        eyebrow="Directory"
        title="Find a hostel near you"
        description="Every hostel on the platform, searchable in one place — with star ratings and reviews from people who've actually lived there."
      />
      <Section width="wide">
        <div className="space-y-6">
          <DirectoryFilters />
          <HostelGrid hostels={page.items} next={page.next} />
        </div>
      </Section>
    </>
  );
}
