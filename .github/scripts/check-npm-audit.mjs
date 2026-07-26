#!/usr/bin/env node
// Gate on `npm audit --json` output against a reviewed allowlist (see
// .github/security/npm-audit-allowlist.json) instead of the raw exit code, so
// a genuinely new high+ severity advisory still fails CI while advisories
// that are only reachable via an upstream package's own vendored/pinned
// dependency (nothing our overrides can reach) don't block every push.
import { readFileSync } from "node:fs";

const [, , reportPath, allowlistPath] = process.argv;
if (!reportPath || !allowlistPath) {
  console.error("usage: check-npm-audit.mjs <npm-audit.json> <allowlist.json>");
  process.exit(2);
}

const report = JSON.parse(readFileSync(reportPath, "utf8"));
if (report.error) {
  console.error("npm audit itself failed to run:", report.error);
  process.exit(1);
}

const allowlist = JSON.parse(readFileSync(allowlistPath, "utf8"));
const allowedIds = new Set(allowlist.advisories.map((a) => a.id));

const found = new Map();
for (const vuln of Object.values(report.vulnerabilities ?? {})) {
  for (const via of vuln.via ?? []) {
    if (typeof via !== "object") continue; // a bare dependency name, not an advisory
    const id = (via.url ?? "").split("/").pop();
    if (!id) continue;
    found.set(id, via.title ?? id);
  }
}

const unallowed = [...found.entries()].filter(([id]) => !allowedIds.has(id));

if (unallowed.length > 0) {
  console.error(
    `${unallowed.length} high+ severity advisor${unallowed.length === 1 ? "y" : "ies"} not covered by the allowlist:`,
  );
  for (const [id, title] of unallowed) console.error(`  - ${id}: ${title}`);
  console.error(
    "\nFix the dependency, or if it is genuinely unfixable today (vendored/pinned by " +
      "an upstream package), add a justified, dated entry to " +
      ".github/security/npm-audit-allowlist.json.",
  );
  process.exit(1);
}

if (found.size > 0) {
  console.log(
    `npm audit: ${found.size} advisor${found.size === 1 ? "y" : "ies"} present, all explicitly allowlisted:`,
  );
  for (const [id, title] of found) {
    const entry = allowlist.advisories.find((a) => a.id === id);
    console.log(`  - ${id}: ${title}`);
    console.log(`    reason: ${entry.reason} (reviewed ${entry.reviewedOn})`);
  }
} else {
  console.log("npm audit: no high+ severity advisories.");
}
