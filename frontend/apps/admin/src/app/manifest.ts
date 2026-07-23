import type { MetadataRoute } from "next";

/**
 * Web App Manifest, served by Next at /manifest.webmanifest and auto-linked
 * into <head> from the App Router. This replaces the old static
 * public/manifest.json so the manifest stays typed and in one place.
 *
 * Brand colors mirror src/app/globals.css (--accent #2563eb, --background #f8fafc).
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "MY Hostel",
    short_name: "MH",
    description:
      "Manage residents, rooms, billing, payments and occupancy for your hostel — online and offline.",
    // "/" resolves to the right place based on session; the query lets us
    // measure launches from the installed app.
    start_url: "/?source=pwa",
    scope: "/",
    display: "standalone",
    // Progressive enhancement: use Window Controls Overlay on desktop where
    // supported, fall back to standalone, then to a normal browser tab.
    display_override: ["window-controls-overlay", "standalone", "browser"],
    orientation: "any",
    theme_color: "#2563eb",
    background_color: "#f8fafc",
    lang: "en",
    dir: "ltr",
    categories: ["business", "productivity", "utilities"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      {
        name: "Dashboard",
        short_name: "Dashboard",
        description: "Occupancy and billing overview",
        url: "/dashboard?source=pwa-shortcut",
        icons: [{ src: "/icons/shortcut-dashboard.png", sizes: "96x96", type: "image/png" }],
      },
      {
        name: "Residents",
        short_name: "Residents",
        description: "Resident directory",
        url: "/residents?source=pwa-shortcut",
        icons: [{ src: "/icons/shortcut-residents.png", sizes: "96x96", type: "image/png" }],
      },
      {
        name: "Payments",
        short_name: "Payments",
        description: "Payments ledger",
        url: "/payments?source=pwa-shortcut",
        icons: [{ src: "/icons/shortcut-payments.png", sizes: "96x96", type: "image/png" }],
      },
    ],
    screenshots: [
      {
        src: "/screenshots/wide.png",
        sizes: "1280x720",
        type: "image/png",
        form_factor: "wide",
        label: "Dashboard on desktop",
      },
      {
        src: "/screenshots/narrow.png",
        sizes: "720x1280",
        type: "image/png",
        form_factor: "narrow",
        label: "Dashboard on mobile",
      },
    ],
    prefer_related_applications: false,
  };
}
