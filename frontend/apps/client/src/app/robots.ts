import type { MetadataRoute } from "next";
import { SITE_URL } from "@/features/landing/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Keep authenticated app surfaces out of the index.
        disallow: ["/dashboard", "/api/", "/offline"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
