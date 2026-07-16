import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Workspace-wide unit test runner: one project per app (each with its own
// `@/` alias) plus one for the shared packages (which only use relative and
// @hostel/* imports, resolved through the workspace symlinks).
const shared = {
  environment: "jsdom" as const,
  globals: true,
  setupFiles: [fileURLToPath(new URL("./vitest.setup.ts", import.meta.url))],
  css: false,
};

export default defineConfig({
  test: {
    // Coverage gate (Phase 0, §2 CI / DEVOPS_AUDIT #9). Enabled only when the
    // runner passes `--coverage` (CI's test:coverage script). Thresholds are a
    // regression FLOOR set just under the current measured baseline — they stop
    // coverage sliding backwards without blocking today's build. Ratchet these
    // up as meaningful suites are added.
    coverage: {
      provider: "v8",
      reporter: ["text-summary", "json-summary", "lcov"],
      // Only files exercised by tests are measured (no `all: true`), matching
      // how the baseline floor below was established.
      thresholds: {
        statements: 48,
        branches: 38,
        functions: 35,
        lines: 50,
      },
    },
    projects: [
      {
        plugins: [react()],
        resolve: {
          alias: { "@": fileURLToPath(new URL("./apps/admin/src", import.meta.url)) },
        },
        test: {
          ...shared,
          name: "admin",
          include: ["apps/admin/src/**/*.{test,spec}.{ts,tsx}"],
        },
      },
      {
        plugins: [react()],
        resolve: {
          alias: { "@": fileURLToPath(new URL("./apps/client/src", import.meta.url)) },
        },
        test: {
          ...shared,
          name: "client",
          include: ["apps/client/src/**/*.{test,spec}.{ts,tsx}"],
        },
      },
      {
        plugins: [react()],
        test: {
          ...shared,
          name: "packages",
          include: ["packages/*/src/**/*.{test,spec}.{ts,tsx}"],
        },
      },
    ],
  },
});
