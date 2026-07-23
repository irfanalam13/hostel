"use client";
import React from "react";

export function Table({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-auto rounded-[20px] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)]">
      <table className="min-w-full text-sm">{children}</table>
    </div>
  );
}
