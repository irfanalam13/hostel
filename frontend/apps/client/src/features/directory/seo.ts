import { SITE_URL } from "@/features/landing/seo";
import type { DirectoryHostel } from "./api";

/**
 * JSON-LD for the /hostels directory listing: a CollectionPage whose
 * mainEntity is an ItemList of the currently-visible LodgingBusiness
 * entries. Only describes what's rendered on this page load (not the full,
 * filtered-out catalog), matching what search engines actually see.
 */
export function buildDirectoryJsonLd(hostels: DirectoryHostel[]) {
  return {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "@id": `${SITE_URL}/hostels`,
    url: `${SITE_URL}/hostels`,
    name: "Find a hostel",
    mainEntity: {
      "@type": "ItemList",
      itemListElement: hostels.map((hostel, i) => ({
        "@type": "ListItem",
        position: i + 1,
        item: {
          "@type": "LodgingBusiness",
          name: hostel.name,
          url: hostel.public_url || undefined,
          ...(hostel.city || hostel.district
            ? {
                address: {
                  "@type": "PostalAddress",
                  addressLocality: hostel.city || undefined,
                  addressRegion: hostel.district || undefined,
                },
              }
            : {}),
          ...(hostel.rating_count > 0
            ? {
                aggregateRating: {
                  "@type": "AggregateRating",
                  ratingValue: hostel.average_rating,
                  reviewCount: hostel.rating_count,
                },
              }
            : {}),
        },
      })),
    },
  };
}
