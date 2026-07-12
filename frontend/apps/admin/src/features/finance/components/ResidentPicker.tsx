"use client";

import React, { useEffect, useState } from "react";
import { Input, Select } from "@hostel/ui";

import { financeApi } from "../api/finance.api";
import type { ResidentOption } from "../types/finance.types";

/**
 * Debounced searchable resident picker: a search box that filters a native
 * <select>. Reused by the invoice / payment / refund / award forms.
 */
export function ResidentPicker({
  label = "Resident",
  value,
  onChange,
  placeholder = "Select a resident",
}: {
  label?: string;
  value: string;
  onChange: (id: string) => void;
  placeholder?: string;
}) {
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<ResidentOption[]>([]);

  useEffect(() => {
    let active = true;
    const t = setTimeout(() => {
      financeApi.residents
        .list(search)
        .then((r) => {
          if (active) setOptions(r);
        })
        .catch(() => {});
    }, 200);
    return () => {
      active = false;
      clearTimeout(t);
    };
  }, [search]);

  return (
    <div className="space-y-2">
      <Input
        label={label}
        placeholder="Search residents by name…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <Select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.full_name}
          </option>
        ))}
      </Select>
    </div>
  );
}
