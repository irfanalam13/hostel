#!/usr/bin/env python3
"""Render a Cobertura coverage.xml as a Markdown table into the GitHub job summary.

Usage:  coverage_summary.py <coverage.xml> [title]

Writes to $GITHUB_STEP_SUMMARY when set (the CI job summary panel), otherwise to
stdout so the same command is useful locally. Never fails the build: a missing or
unparseable report degrades to a one-line note rather than masking the real
pytest exit code (the coverage *gate* is enforced by pytest's --cov-fail-under).
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "coverage.xml"
    title = sys.argv[2] if len(sys.argv) > 2 else "Coverage"

    lines: list[str] = [f"### 🧪 {title}", ""]
    try:
        root = ET.parse(path).getroot()
        line_rate = float(root.get("line-rate", 0)) * 100
        branch_rate = float(root.get("branch-rate", 0)) * 100
        lines += [
            "| Metric | Coverage |",
            "| --- | --- |",
            f"| Lines | **{line_rate:.1f}%** |",
            f"| Branches | {branch_rate:.1f}% |",
            "",
            "<details><summary>Per-package</summary>",
            "",
            "| Package | Lines |",
            "| --- | --- |",
        ]
        packages = root.findall(".//package")
        for pkg in sorted(packages, key=lambda p: p.get("name", "")):
            pkg_rate = float(pkg.get("line-rate", 0)) * 100
            lines.append(f"| `{pkg.get('name', '?')}` | {pkg_rate:.1f}% |")
        lines += ["", "</details>"]
    except (OSError, ET.ParseError) as exc:  # pragma: no cover - reporting only
        lines.append(f"_Coverage report unavailable: {exc}_")

    output = "\n".join(lines) + "\n"
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(output)
    else:
        # Write UTF-8 bytes directly so the emoji-bearing summary survives a
        # non-UTF-8 console (e.g. Windows cp1252) when run locally.
        sys.stdout.buffer.write(output.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
