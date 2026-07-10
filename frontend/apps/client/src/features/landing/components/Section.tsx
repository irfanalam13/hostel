import React from "react";
import { Container } from "./Container";

type Tone = "default" | "muted" | "accent-soft";

type Props = React.HTMLAttributes<HTMLElement> & {
  /** Anchor id for in-page nav (e.g. "features", "pricing"). */
  id?: string;
  /** Background tone, mapped to theme tokens (light/dark safe). */
  tone?: Tone;
  /** Container width passed through to the inner Container. */
  width?: "default" | "narrow" | "wide";
  /** Set false to render children edge-to-edge without the inner Container. */
  contained?: boolean;
};

const TONES: Record<Tone, string> = {
  default: "bg-[var(--background)]",
  muted: "bg-[var(--background-secondary)]",
  "accent-soft": "bg-[var(--accent-soft)]",
};

/**
 * Vertical rhythm wrapper for landing sections. Provides consistent spacing
 * and tone; wrap content in the shared Container by default.
 */
export function Section({
  id,
  tone = "default",
  width = "default",
  contained = true,
  className = "",
  children,
  ...props
}: Props) {
  return (
    <section
      id={id}
      // scroll-mt offsets the sticky navbar when jumping to an anchor.
      className={`scroll-mt-24 py-16 sm:py-20 lg:py-28 ${TONES[tone]} ${className}`}
      {...props}
    >
      {contained ? <Container width={width}>{children}</Container> : children}
    </section>
  );
}
