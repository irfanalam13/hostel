"use client";

import { useEffect, useState } from "react";
import { createNotice, listNotices, updateNotice } from "@/features/notices/api";
import type { Notice } from "@/features/notices/types";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Table } from "@/shared/ui/Table";
import { Topbar } from "@/shared/ui/Topbar";

export default function NoticesPage() {
  const [rows, setRows] = useState<Notice[]>([]);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    title: "",
    body: "",
    target_type: "ALL",
    target_value: "",
    is_pinned: false,
  });

  async function refresh() {
    try {
      setRows(await listNotices());
    } catch (err: any) {
      setMessage(err?.message || "Failed to load notices.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await createNotice({
      ...form,
      target_type: form.target_type as Notice["target_type"],
    });
    setForm({ title: "", body: "", target_type: "ALL", target_value: "", is_pinned: false });
    setMessage("Notice published.");
    await refresh();
  }

  async function togglePin(row: Notice) {
    await updateNotice(row.id, { is_pinned: !row.is_pinned });
    await refresh();
  }

  return (
    <div>
      <Topbar title="Notices" />
      {message ? <div className="mb-3 text-sm text-zinc-700">{message}</div> : null}

      <form onSubmit={save} className="mb-4 grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-4">
        <Input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.target_type} onChange={(e) => setForm({ ...form, target_type: e.target.value })}>
          <option value="ALL">All</option>
          <option value="BLOCK">Block</option>
          <option value="FLOOR">Floor</option>
          <option value="ROOM">Room</option>
          <option value="ROLE">Role</option>
        </select>
        <Input placeholder="Target value" value={form.target_value} onChange={(e) => setForm({ ...form, target_value: e.target.value })} />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_pinned} onChange={(e) => setForm({ ...form, is_pinned: e.target.checked })} />
          Pin
        </label>
        <textarea className="md:col-span-4 rounded-lg border border-gray-200 px-3 py-2" placeholder="Notice body" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required />
        <Button type="submit">Publish</Button>
      </form>

      <Table>
        <thead>
          <tr className="border-b text-left">
            <th className="p-3">Notice</th>
            <th className="p-3">Target</th>
            <th className="p-3">Pinned</th>
            <th className="p-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b">
              <td className="p-3">
                <div className="font-medium">{row.title}</div>
                <div className="text-xs text-zinc-500 line-clamp-2">{row.body}</div>
              </td>
              <td className="p-3">{row.target_type}{row.target_value ? `: ${row.target_value}` : ""}</td>
              <td className="p-3">{row.is_pinned ? "Yes" : "No"}</td>
              <td className="p-3"><Button variant="ghost" onClick={() => togglePin(row)}>{row.is_pinned ? "Unpin" : "Pin"}</Button></td>
            </tr>
          ))}
          {!rows.length ? (
            <tr><td className="p-6 text-center text-sm text-zinc-500" colSpan={4}>No notices yet.</td></tr>
          ) : null}
        </tbody>
      </Table>
    </div>
  );
}
