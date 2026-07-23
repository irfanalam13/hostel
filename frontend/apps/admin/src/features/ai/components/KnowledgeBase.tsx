"use client";

import React, { useRef, useState } from "react";
import { useApi } from "@hostel/hooks";
import { Button, Spinner, useToast } from "@hostel/ui";
import { FileText, RefreshCw, Trash2, Upload } from "lucide-react";

import { aiApi } from "../api/ai.api";
import type { KnowledgeDocument } from "../types/ai.types";

const STATUS_STYLE: Record<KnowledgeDocument["status"], string> = {
  READY: "bg-[var(--success)]/15 text-[var(--success)]",
  PENDING: "bg-[var(--warning)]/15 text-[var(--warning)]",
  INGESTING: "bg-[var(--warning)]/15 text-[var(--warning)]",
  FAILED: "bg-[var(--error)]/15 text-[var(--error)]",
};

export function KnowledgeBase() {
  const toast = useToast();
  const { data, loading, refetch } = useApi(() => aiApi.knowledge.list(), {
    immediate: true,
    deps: [],
  });

  const [mode, setMode] = useState<"text" | "file">("text");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [visibility, setVisibility] = useState("STAFF");
  const [saving, setSaving] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const docs = data ?? [];

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      if (mode === "text") {
        if (!content.trim()) {
          toast.error("Add some text content to ingest.");
          return;
        }
        await aiApi.knowledge.createText({ title: title.trim(), content, visibility });
      } else {
        const file = fileRef.current?.files?.[0];
        if (!file) {
          toast.error("Choose a file to upload.");
          return;
        }
        const form = new FormData();
        form.append("title", title.trim());
        form.append("source_type", "UPLOAD");
        form.append("visibility", visibility);
        form.append("file", file);
        await aiApi.knowledge.createFile(form);
      }
      toast.success("Document added — ingesting in the background.");
      setTitle("");
      setContent("");
      if (fileRef.current) fileRef.current.value = "";
      refetch();
    } catch (err) {
      const detail = (err as { data?: { message?: string } })?.data?.message;
      toast.error(detail || "Could not add the document.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(doc: KnowledgeDocument) {
    if (!confirm(`Delete "${doc.title}" from the knowledge base?`)) return;
    try {
      await aiApi.knowledge.remove(doc.id);
      toast.success("Document removed.");
      refetch();
    } catch {
      toast.error("Could not delete the document.");
    }
  }

  async function reingest(doc: KnowledgeDocument) {
    try {
      await aiApi.knowledge.reingest(doc.id);
      toast.success("Re-ingestion queued.");
      refetch();
    } catch {
      toast.error("Could not re-ingest.");
    }
  }

  return (
    <div className="space-y-5">
      {/* Add document */}
      <form
        onSubmit={submit}
        className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)] space-y-3"
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-[var(--foreground)]">
          <Upload className="h-4 w-4" /> Add to knowledge base
        </div>

        <div className="flex flex-wrap gap-2">
          {(["text", "file"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                mode === m
                  ? "bg-[var(--accent)] text-white"
                  : "border border-[var(--border)] text-[var(--foreground-secondary)]"
              }`}
            >
              {m === "text" ? "Paste text" : "Upload file"}
            </button>
          ))}
        </div>

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Document title (e.g. Hostel Rules 2026)"
          className="w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
        />

        {mode === "text" ? (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={5}
            placeholder="Paste the policy / rules / FAQ text here…"
            className="w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
          />
        ) : (
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt,.md,.csv"
            className="w-full text-sm text-[var(--foreground-secondary)]"
          />
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            Visibility
            <select
              value={visibility}
              onChange={(e) => setVisibility(e.target.value)}
              className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-2 py-1 text-sm text-[var(--foreground)]"
            >
              <option value="STAFF">All staff</option>
              <option value="ADMIN">Admins only</option>
            </select>
          </label>
          <Button type="submit" disabled={saving}>
            {saving ? "Adding…" : "Add document"}
          </Button>
        </div>
      </form>

      {/* Document list */}
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)]">
        <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
          <div className="text-sm font-semibold text-[var(--foreground)]">Documents</div>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1 text-xs text-[var(--muted)] hover:text-[var(--foreground)]"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>

        {loading && !data ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : docs.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-[var(--muted)]">
            No documents yet. Add policies, rules or FAQs so the assistant can cite them.
          </div>
        ) : (
          <ul className="divide-y divide-[var(--border)]">
            {docs.map((doc) => (
              <li key={doc.id} className="flex items-center gap-3 px-4 py-3">
                <FileText className="h-4 w-4 shrink-0 text-[var(--muted)]" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-[var(--foreground)]">
                    {doc.title}
                  </div>
                  <div className="text-xs text-[var(--muted)]">
                    {doc.source_type} · {doc.visibility === "ADMIN" ? "Admins only" : "All staff"}
                    {doc.status === "READY" ? ` · ${doc.chunk_count} chunks` : ""}
                    {doc.status === "FAILED" && doc.error ? ` · ${doc.error}` : ""}
                  </div>
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLE[doc.status]}`}
                >
                  {doc.status}
                </span>
                {doc.status === "FAILED" ? (
                  <button
                    onClick={() => reingest(doc)}
                    className="text-[var(--muted)] hover:text-[var(--foreground)]"
                    aria-label="Re-ingest"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </button>
                ) : null}
                <button
                  onClick={() => remove(doc)}
                  className="text-[var(--muted)] hover:text-[var(--error)]"
                  aria-label="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
