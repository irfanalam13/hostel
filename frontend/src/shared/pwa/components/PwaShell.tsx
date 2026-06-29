"use client";

import { InstallPrompt } from "./InstallPrompt";
import { OfflineBanner } from "./OfflineBanner";
import { UpdateBanner } from "./UpdateBanner";

/**
 * Mounts all global PWA UI affordances. Rendered once by PwaProvider so the
 * banners are available on every route (public and protected).
 */
export function PwaShell() {
  return (
    <>
      <OfflineBanner />
      <UpdateBanner />
      <InstallPrompt />
    </>
  );
}
