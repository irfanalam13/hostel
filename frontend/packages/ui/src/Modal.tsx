"use client";

import React from "react";
import { Button } from "./Button";

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-3xl border border-[var(--border)] bg-[var(--card-elevated)] p-4 shadow-[var(--shadow-lg)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="text-base font-semibold text-[var(--foreground)]">{title}</div>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}
