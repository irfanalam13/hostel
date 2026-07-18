import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "react-hooks/set-state-in-effect": "off",
      // Honour the `_`-prefix convention for intentionally-unused bindings
      // (back-compat shim args, ignored destructure slots, swallowed errors).
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          destructuredArrayIgnorePattern: "^_",
        },
      ],
    },
  },
  // E2E / Cypress test tooling is not React app code: Playwright fixtures take a
  // `use` callback (not the React `use` hook) and Cypress augments its types via
  // `namespace`. Disable the React/TS rules that misfire on that infrastructure.
  {
    files: ["e2e/**", "cypress/**"],
    rules: {
      "react-hooks/rules-of-hooks": "off",
      "@typescript-eslint/no-namespace": "off",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "apps/*/.next/**",
    "apps/*/out/**",
    "apps/*/next-env.d.ts",
    // Generated artifacts — never lint these.
    "coverage/**",
    "apps/*/coverage/**",
    "playwright-report/**",
    "test-results/**",
  ]),
]);

export default eslintConfig;
