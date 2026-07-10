"use client";

import { useEffect, useState } from "react";

export type DeviceType = "mobile" | "tablet" | "desktop";
export type OS = "ios" | "android" | "windows" | "macos" | "linux" | "unknown";

export type Platform = {
  /** True once detection has run on the client (use to gate render & avoid SSR mismatch). */
  mounted: boolean;
  type: DeviceType;
  os: OS;
  isTouch: boolean;
  /** Human label, e.g. "Windows desktop". */
  label: string;
};

const SSR_DEFAULT: Platform = {
  mounted: false,
  type: "desktop",
  os: "unknown",
  isTouch: false,
  label: "",
};

const OS_LABEL: Record<OS, string> = {
  ios: "iOS",
  android: "Android",
  windows: "Windows",
  macos: "macOS",
  linux: "Linux",
  unknown: "",
};

function detect(): Omit<Platform, "mounted"> {
  const ua = (navigator.userAgent || "").toLowerCase();
  const maxTouch = navigator.maxTouchPoints || 0;
  const isTouch = maxTouch > 0 || "ontouchstart" in window;
  // iPadOS 13+ reports a Mac UA; disambiguate via multi-touch support.
  const isIpadOS = navigator.platform === "MacIntel" && maxTouch > 1;

  let os: OS = "unknown";
  if (/iphone|ipod/.test(ua) || /ipad/.test(ua) || isIpadOS) os = "ios";
  else if (/android/.test(ua)) os = "android";
  else if (/windows/.test(ua)) os = "windows";
  else if (/macintosh|mac os x/.test(ua)) os = "macos";
  else if (/linux/.test(ua)) os = "linux";

  const width = window.innerWidth;
  const isPhone =
    /iphone|ipod/.test(ua) || (os === "android" && /mobile/.test(ua)) || (isTouch && width < 768);
  const isTablet =
    !isPhone &&
    (/ipad/.test(ua) ||
      isIpadOS ||
      (os === "android" && !/mobile/.test(ua)) ||
      (isTouch && width >= 768 && width < 1024));

  const type: DeviceType = isPhone ? "mobile" : isTablet ? "tablet" : "desktop";
  const label = `${OS_LABEL[os]} ${type}`.trim();

  return { type, os, isTouch, label };
}

/**
 * Client-side device/OS detection. SSR-safe: returns a stable desktop default
 * with `mounted: false` on the server and first client render, then resolves to
 * the real device after mount. Gate any platform-specific UI on `mounted`.
 */
export function usePlatform(): Platform {
  const [state, setState] = useState<Platform>(SSR_DEFAULT);

  useEffect(() => {
    setState({ mounted: true, ...detect() });
  }, []);

  return state;
}

/** Step-by-step manual install instructions tailored to the OS. */
export function manualInstallSteps(os: OS): string[] {
  switch (os) {
    case "ios":
      return [
        "Open this site in Safari",
        "Tap the Share button",
        "Choose “Add to Home Screen”, then “Add”",
      ];
    case "android":
      return [
        "Open the browser menu (⋮)",
        "Tap “Install app” or “Add to Home screen”",
        "Confirm to install",
      ];
    case "windows":
    case "macos":
    case "linux":
      return [
        "Click the install icon in the address bar",
        "Or open the browser menu and choose “Install”",
        "Confirm to install",
      ];
    default:
      return ["Open your browser menu", "Choose “Install app” / “Add to Home Screen”"];
  }
}

/** One-line manual install hint for toasts. */
export function manualInstallHint(os: OS): string {
  switch (os) {
    case "ios":
      return "In Safari, tap the Share button, then “Add to Home Screen”.";
    case "android":
      return "Open your browser menu (⋮) and tap “Install app”.";
    case "windows":
    case "macos":
    case "linux":
      return "Click the install icon in your browser’s address bar, or use the menu → “Install”.";
    default:
      return "Open your browser menu and choose “Add to Home Screen” / “Install app”.";
  }
}
