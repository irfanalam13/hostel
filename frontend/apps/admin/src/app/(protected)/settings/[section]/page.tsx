"use client";

import { useParams } from "next/navigation";
import { SettingsShell } from "@/features/settings/components/SettingsShell";

export default function SettingsSectionPage() {
  const params = useParams();
  const section = (Array.isArray(params?.section) ? params.section[0] : params?.section) || "home";
  return <SettingsShell section={section} />;
}
