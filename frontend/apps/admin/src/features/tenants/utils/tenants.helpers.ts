export function formatDate(d?: string | null) {
  if (!d) return "-";
  try {
    return new Date(d).toLocaleDateString();
  } catch {
    return d;
  }
}

export function yesNo(v: boolean) {
  return v ? "Yes" : "No";
}