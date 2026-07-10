"use client";

import { useEffect, useState } from "react";
import { tenantsApi } from "../api/tenants.api";
import type { Hostel } from "../types/tenants.types";
import { authStore } from "@hostel/auth";
import { Button } from "@hostel/ui";
import { Card } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Spinner } from "@hostel/ui";
import { useToast } from "@hostel/ui";

/**
 * Lets staff edit the active hostel's admission-related settings
 * (Hostel.settings JSON consumed by apps/admissions).
 */
export function HostelSettingsCard() {
  const toast = useToast();
  const [hostel, setHostel] = useState<Hostel | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [fee, setFee] = useState("");
  const [maxSize, setMaxSize] = useState("");

  useEffect(() => {
    const code = authStore.getHostelCode();
    tenantsApi.hostels
      .list()
      .then((hostels) => {
        const current = hostels.find((h) => h.code === code) || hostels[0] || null;
        if (current) {
          setHostel(current);
          setFee(String(current.settings?.default_application_fee ?? 500));
          setMaxSize(String(current.settings?.max_upload_size_mb ?? 10));
        }
      })
      .catch(() => {
        /* non-staff users can't list hostels — hide silently */
      })
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    if (!hostel) return;
    setSaving(true);
    try {
      const updated = await tenantsApi.hostels.update(hostel.id, {
        settings: {
          ...hostel.settings,
          default_application_fee: Number(fee) || 0,
          max_upload_size_mb: Number(maxSize) || 10,
        },
      });
      setHostel(updated);
      toast.success("Hostel settings saved.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <div className="grid place-items-center py-6">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (!hostel) return null;

  return (
    <Card>
      <div className="mb-3 text-sm font-semibold">Admission Settings — {hostel.name}</div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Default application fee (Rs)"
          type="number"
          value={fee}
          onChange={(e) => setFee(e.target.value)}
        />
        <Input
          label="Max document upload size (MB)"
          type="number"
          value={maxSize}
          onChange={(e) => setMaxSize(e.target.value)}
        />
      </div>
      <div className="mt-3 flex justify-end">
        <Button loading={saving} onClick={save}>
          Save settings
        </Button>
      </div>
    </Card>
  );
}
