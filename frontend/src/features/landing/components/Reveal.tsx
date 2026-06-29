"use client";

import React from "react";
import { useInView } from "../hooks/useInView";

type Props = {
  children: React.ReactNode;
  /** Stagger delay in ms for sequenced reveals. */
  delay?: number;
  as?: React.ElementType;
  className?: string;
};

/**
 * Wraps content in a scroll-triggered fade/slide reveal. Honors
 * prefers-reduced-motion (via useInView) and never hides content from crawlers
 * — the markup is always present; only the CSS transition is gated.
 */
export function Reveal({ children, delay = 0, as: Tag = "div", className = "" }: Props) {
  const { ref, inView } = useInView<HTMLDivElement>();

  return (
    <Tag
      ref={ref}
      className={`reveal ${inView ? "is-visible" : ""} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </Tag>
  );
}
