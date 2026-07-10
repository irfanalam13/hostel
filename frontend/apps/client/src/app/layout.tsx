import "./globals.css";
import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";

// Strict CSP requires a fresh per-request nonce (see src/proxy.ts). Next can
// only stamp that nonce onto its <script> tags while rendering a request — it
// cannot inject it into statically prerendered HTML built ahead of time.
// Forcing dynamic rendering keeps the nonce valid on every marketing page.
// (SSR still emits full HTML, so SEO is unaffected.)
export const dynamic = "force-dynamic";

const APP_NAME = "MY Hostel";
const APP_DESC =
  "Manage residents, rooms, billing, payments and occupancy for your hostel — online and offline.";

export const metadata: Metadata = {
  applicationName: APP_NAME,
  title: { default: "Hostel SaaS", template: "%s · Hostel SaaS" },
  description: APP_DESC,
  // The PWA (manifest + icons + sw.js) is owned by the admin zone and served
  // through the fallback rewrites, so these URLs stay valid on this origin.
  manifest: "/manifest.webmanifest",
  formatDetection: { telephone: false },
  icons: {
    icon: [
      { url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon.ico" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  openGraph: {
    type: "website",
    siteName: APP_NAME,
    title: APP_NAME,
    description: APP_DESC,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#2563eb" },
    { media: "(prefers-color-scheme: dark)", color: "#020617" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-[var(--background)] text-[var(--foreground)] antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
