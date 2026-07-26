"use client";

import React from "react";
import { websiteApi, type FieldKind, type FieldSchema } from "../api/website.api";

/**
 * Schema-driven section editor: renders inputs straight from the backend
 * section registry (`section_types[type].fields`), so every section type —
 * including ones added later — is editable with zero builder-UI changes.
 *
 * Supported field kinds: text, textarea, url, number, boolean,
 * image (URL + upload button), and list (repeatable rows of the above).
 */

type Content = Record<string, unknown>;

const inputCls =
  "w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm " +
  "text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]";

function label(name: string): string {
  return name.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function ImageField({
  value, onChange,
}: { value: string; onChange: (v: string) => void }) {
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState("");
  const fileRef = React.useRef<HTMLInputElement>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const media = await websiteApi.uploadMedia(file);
      onChange(media.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div>
      <div className="flex gap-2">
        <input
          className={inputCls}
          placeholder="Image URL — or upload →"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="shrink-0 rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-semibold text-[var(--foreground)] hover:border-[var(--accent)] disabled:opacity-50"
        >
          {uploading ? "Uploading…" : "Upload"}
        </button>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onFile} />
      </div>
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
      {value && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={value} alt="" className="mt-2 h-16 rounded-lg object-cover" />
      )}
    </div>
  );
}

function ScalarField({
  kind, value, onChange,
}: { kind: FieldKind; value: unknown; onChange: (v: unknown) => void }) {
  switch (kind) {
    case "textarea":
      return (
        <textarea rows={3} className={inputCls} value={String(value ?? "")}
                  onChange={(e) => onChange(e.target.value)} />
      );
    case "boolean":
      return (
        <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <input type="checkbox" checked={value !== false && value !== undefined ? Boolean(value) : false}
                 onChange={(e) => onChange(e.target.checked)} className="h-4 w-4" />
          Enabled
        </label>
      );
    case "number":
      return (
        <input type="number" className={inputCls} value={value === undefined || value === "" ? "" : Number(value)}
               onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))} />
      );
    case "image":
      return <ImageField value={String(value ?? "")} onChange={onChange} />;
    default: // text | url
      return (
        <input className={inputCls} value={String(value ?? "")}
               onChange={(e) => onChange(e.target.value)} />
      );
  }
}

function ListField({
  fields, items, onChange,
}: {
  fields: Record<string, FieldKind>;
  items: Content[];
  onChange: (items: Content[]) => void;
}) {
  function update(index: number, key: string, value: unknown) {
    const next = items.map((it, i) => (i === index ? { ...it, [key]: value } : it));
    onChange(next);
  }
  function add() {
    const blank: Content = {};
    for (const [key, kind] of Object.entries(fields)) {
      blank[key] = kind === "boolean" ? true : kind === "number" ? 0 : "";
    }
    onChange([...items, blank]);
  }
  function remove(index: number) {
    onChange(items.filter((_, i) => i !== index));
  }
  function move(index: number, delta: number) {
    const to = index + delta;
    if (to < 0 || to >= items.length) return;
    const next = [...items];
    [next[index], next[to]] = [next[to], next[index]];
    onChange(next);
  }

  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className="rounded-xl border border-[var(--border)] p-3">
          <div className="mb-2 flex items-center justify-between text-xs text-[var(--muted)]">
            <span>#{i + 1}</span>
            <span className="flex gap-2">
              <button type="button" onClick={() => move(i, -1)} disabled={i === 0}
                      className="hover:text-[var(--accent)] disabled:opacity-30">↑</button>
              <button type="button" onClick={() => move(i, 1)} disabled={i === items.length - 1}
                      className="hover:text-[var(--accent)] disabled:opacity-30">↓</button>
              <button type="button" onClick={() => remove(i)} className="text-red-500 hover:underline">
                Remove
              </button>
            </span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {Object.entries(fields).map(([key, kind]) => (
              <div key={key} className={kind === "textarea" ? "sm:col-span-2" : ""}>
                <div className="mb-1 text-xs font-medium text-[var(--muted)]">{label(key)}</div>
                <ScalarField kind={kind} value={item[key]} onChange={(v) => update(i, key, v)} />
              </div>
            ))}
          </div>
        </div>
      ))}
      <button type="button" onClick={add}
              className="rounded-lg border border-dashed border-[var(--border)] px-3 py-2 text-xs font-semibold text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--accent)]">
        + Add item
      </button>
    </div>
  );
}

export function SectionForm({
  schema, content, onChange,
}: {
  schema: FieldSchema;
  content: Content;
  onChange: (content: Content) => void;
}) {
  function set(key: string, value: unknown) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="space-y-4">
      {Object.entries(schema).map(([key, def]) => (
        <div key={key}>
          <div className="mb-1 text-sm font-medium text-[var(--foreground)]">{label(key)}</div>
          {typeof def === "object" && def.kind === "list" ? (
            <ListField
              fields={def.fields}
              items={Array.isArray(content[key]) ? (content[key] as Content[]) : []}
              onChange={(items) => set(key, items)}
            />
          ) : (
            <ScalarField kind={def as FieldKind} value={content[key]} onChange={(v) => set(key, v)} />
          )}
        </div>
      ))}
    </div>
  );
}
