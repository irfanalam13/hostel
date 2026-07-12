"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useToast } from "@hostel/ui";
import { workspaceApi, type SettingsNamespace } from "../api/workspace.api";

/**
 * Schema-driven settings form for one workspace-settings namespace.
 *
 * The backend returns `defaults` alongside the stored values; input types are
 * inferred from the default's JS type (boolean → toggle, number → number
 * input, string → text, nested object → grouped sub-fields). New keys added
 * to a namespace on the backend appear here automatically.
 */

type Values = Record<string, unknown>;

const inputCls =
  "w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm " +
  "text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]";
const card = "rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5";

function label(name: string): string {
  return name.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 rounded-full transition ${checked ? "bg-[var(--accent)]" : "bg-gray-400/40"}`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? "left-[22px]" : "left-0.5"}`}
      />
    </button>
  );
}

function Field({
  name, value, defaultValue, onChange,
}: { name: string; value: unknown; defaultValue: unknown; onChange: (v: unknown) => void }) {
  if (typeof defaultValue === "boolean") {
    return (
      <div className="flex items-center justify-between gap-3 py-1.5">
        <span className="text-sm text-[var(--foreground)]">{label(name)}</span>
        <Toggle checked={Boolean(value)} onChange={onChange} />
      </div>
    );
  }
  if (typeof defaultValue === "number") {
    return (
      <div>
        <div className="mb-1 text-xs font-medium text-[var(--muted)]">{label(name)}</div>
        <input
          type="number" className={inputCls}
          value={value === undefined || value === "" ? "" : Number(value)}
          onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
        />
      </div>
    );
  }
  if (typeof defaultValue === "string") {
    const long = name.includes("description") || name.includes("address");
    return (
      <div>
        <div className="mb-1 text-xs font-medium text-[var(--muted)]">{label(name)}</div>
        {long ? (
          <textarea rows={3} className={inputCls} value={String(value ?? "")}
                    onChange={(e) => onChange(e.target.value)} />
        ) : (
          <input className={inputCls} value={String(value ?? "")}
                 onChange={(e) => onChange(e.target.value)} />
        )}
      </div>
    );
  }
  return null; // lists are managed elsewhere (future)
}

export function NamespaceForm({
  namespace, title, description,
}: { namespace: SettingsNamespace; title: string; description: string }) {
  const toast = useToast();
  const [values, setValues] = useState<Values | null>(null);
  const [defaults, setDefaults] = useState<Values>({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const payload = await workspaceApi.getSettings(namespace);
      setValues(payload.settings);
      setDefaults(payload.defaults || payload.settings);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load settings.");
    }
  }, [namespace]);

  useEffect(() => { void load(); }, [load]);

  async function save() {
    if (!values || saving) return;
    setSaving(true);
    try {
      const payload = await workspaceApi.updateSettings(namespace, values);
      setValues(payload.settings);
      toast.success(`${title} saved.`, "Settings updated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save.", "Error");
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return <div className={card}><p className="text-sm text-red-500">{error}</p></div>;
  }
  if (!values) {
    return <div className={card}><p className="text-sm text-[var(--muted)]">Loading…</p></div>;
  }

  const scalarKeys = Object.keys(defaults).filter((k) => typeof defaults[k] !== "object");
  const groupKeys = Object.keys(defaults).filter(
    (k) => defaults[k] && typeof defaults[k] === "object" && !Array.isArray(defaults[k]),
  );

  return (
    <div className={card}>
      <h3 className="text-sm font-bold text-[var(--foreground)]">{title}</h3>
      <p className="mb-4 mt-0.5 text-xs text-[var(--muted)]">{description}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        {scalarKeys.map((key) => (
          <div key={key} className={typeof defaults[key] === "boolean" ? "sm:col-span-2" : ""}>
            <Field
              name={key}
              value={values[key]}
              defaultValue={defaults[key]}
              onChange={(v) => setValues({ ...values, [key]: v })}
            />
          </div>
        ))}
      </div>

      {groupKeys.map((group) => {
        const groupDefaults = defaults[group] as Values;
        const groupValues = (values[group] as Values) || {};
        return (
          <div key={group} className="mt-5 border-t border-[var(--border)] pt-4">
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-[var(--muted)]">
              {label(group)}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {Object.keys(groupDefaults).map((key) => (
                <div key={key} className={typeof groupDefaults[key] === "boolean" ? "sm:col-span-2" : ""}>
                  <Field
                    name={key}
                    value={groupValues[key]}
                    defaultValue={groupDefaults[key]}
                    onChange={(v) =>
                      setValues({ ...values, [group]: { ...groupValues, [key]: v } })}
                  />
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <button
        onClick={() => void save()}
        disabled={saving}
        className="mt-5 rounded-lg bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
      >
        {saving ? "Saving…" : `Save ${title.toLowerCase()}`}
      </button>
    </div>
  );
}
