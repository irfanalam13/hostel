"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { CatalogBrowser } from "@/features/platform/components/CatalogBrowser";

export default function PlatformCatalogPage() {
  return (
    <PlatformShell
      title="Feature catalog"
      description="The master registry of features, categories and limit definitions."
    >
      <CatalogBrowser />
    </PlatformShell>
  );
}
