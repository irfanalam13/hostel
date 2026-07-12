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
