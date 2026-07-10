import React from "react";

type Props = {
  /** Small label above the title (e.g. "Pricing", "Features"). */
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  align?: "center" | "left";
  /** Heading level for correct document outline. Defaults to h2. */
  as?: "h1" | "h2" | "h3";
  className?: string;
};

/**
 * Standard heading block for every section: eyebrow + title + description,
 * with a sensible default outline (h2) and centered alignment.
 */
export function SectionHeader({
  eyebrow,
  title,
  description,
  align = "center",
  as: Heading = "h2",
  className = "",
}: Props) {
  const alignment =
    align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl text-left";

  return (
    <div className={`${alignment} ${className}`}>
      {eyebrow ? (
        <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">
          {eyebrow}
        </p>
      ) : null}
      <Heading className="text-balance text-3xl font-bold tracking-tight text-[var(--foreground)] sm:text-4xl">
        {title}
      </Heading>
      {description ? (
        <p className="mt-4 text-pretty text-base leading-relaxed text-[var(--foreground-secondary)] sm:text-lg">
          {description}
        </p>
      ) : null}
    </div>
  );
}
