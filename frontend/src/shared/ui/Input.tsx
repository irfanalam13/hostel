"use client";

import React from "react";

type Props = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

export function Input({ label, className = "", ...props }: Props) {
  return (
    <label className="block">
      {label ? <div className="text-sm mb-1 text-gray-700">{label}</div> : null}
      <input
        {...props}
        className={`w-full px-3 py-2 rounded-lg border border-gray-200 outline-none focus:ring-2 focus:ring-black ${className}`}
      />
    </label>
  );
}