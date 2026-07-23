export function downloadText(filename: string, content: string, mime = "text/plain") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function downloadJSON(filename: string, obj: unknown) {
  downloadText(filename, JSON.stringify(obj, null, 2), "application/json");
}

// Excel-friendly export (CSV opens in Excel)
export function downloadCSV(filename: string, rows: Record<string, any>[]) {
  if (!rows.length) return downloadText(filename, "", "text/csv");

  const headers = Object.keys(rows[0]);
  const escape = (v: any) => {
    const s = String(v ?? "");
    const needs = s.includes(",") || s.includes('"') || s.includes("\n");
    const cleaned = s.replace(/"/g, '""');
    return needs ? `"${cleaned}"` : cleaned;
  };

  const lines = [
    headers.join(","),
    ...rows.map(r => headers.map(h => escape(r[h])).join(",")),
  ];

  downloadText(filename, lines.join("\n"), "text/csv");
}