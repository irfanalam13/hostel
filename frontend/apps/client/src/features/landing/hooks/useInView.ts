"use client";

import { useEffect, useRef, useState } from "react";

type Options = {
  /** Fraction of the element visible before triggering. */
  threshold?: number;
  /** Trigger once then disconnect (default true). */
  once?: boolean;
  rootMargin?: string;
};

/**
 * Lightweight IntersectionObserver hook for scroll reveals. Zero deps, SSR-safe,
 * and degrades to "always visible" when IntersectionObserver is unavailable or
 * the user prefers reduced motion.
 */
export function useInView<T extends HTMLElement = HTMLDivElement>({
  threshold = 0.15,
  once = true,
  rootMargin = "0px 0px -10% 0px",
}: Options = {}) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    if (reduced || typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setInView(true);
            if (once) observer.disconnect();
          } else if (!once) {
            setInView(false);
          }
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold, once, rootMargin]);

  return { ref, inView };
}
