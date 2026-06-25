"use client";
import React from "react";

export function Table({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-auto rounded-2xl border border-zinc-200 bg-white shadow-sm">
      <table className="min-w-full text-sm">{children}</table>
    </div>
  );
}