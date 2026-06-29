import React from "react";

type Props = React.HTMLAttributes<HTMLDivElement> & {
  /** Render as a different element (e.g. "section", "header", "nav"). */
  as?: React.ElementType;
  /** Max content width. Defaults to the standard marketing width. */
  width?: "default" | "narrow" | "wide";
};

const WIDTHS: Record<NonNullable<Props["width"]>, string> = {
  narrow: "max-w-3xl",
  default: "max-w-6xl",
  wide: "max-w-7xl",
};

/**
 * Single source of truth for horizontal alignment + gutters across every
 * landing section, so all sections share the same edges and breathing space.
 */
export function Container({
  as: Tag = "div",
  width = "default",
  className = "",
  children,
  ...props
}: Props) {
  return (
    <Tag
      {...props}
      className={`mx-auto w-full ${WIDTHS[width]} px-4 sm:px-6 lg:px-8 ${className}`}
    >
      {children}
    </Tag>
  );
}
