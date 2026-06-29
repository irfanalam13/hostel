/// <reference types="cypress" />

/**
 * Custom Cypress commands shared across specs.
 *
 *   cy.mockApi()       — stub the Django API (cookie-auth contract) with cy.intercept.
 *   cy.seedSession()   — set the localStorage session marker AuthProvider checks.
 *   cy.login()         — drive the real login form to an authenticated dashboard.
 */
export {};

const API = "http://localhost:8000/api";
export const TEST_HOSTEL_CODE = "HTL-ABC12345";
const TEST_USER = {
  id: 1,
  username: "warden",
  email: "warden@example.com",
  role: "WARDEN",
  is_staff: true,
  is_active: true,
};

declare global {
  namespace Cypress {
    interface Chainable {
      mockApi(opts?: { unauthenticated?: boolean }): Chainable<void>;
      seedSession(): Chainable<void>;
      login(): Chainable<void>;
    }
  }
}

Cypress.Commands.add("mockApi", (opts: { unauthenticated?: boolean } = {}) => {
  cy.intercept("GET", `${API}/auth/csrf/`, { statusCode: 200, body: { csrftoken: "test-csrf" } });
  cy.intercept("POST", `${API}/auth/login/`, (req) => {
    if (opts.unauthenticated) {
      req.reply({ statusCode: 400, body: { detail: "Invalid credentials." } });
    } else {
      req.reply({ statusCode: 200, body: { detail: "ok", user: TEST_USER, hostel_code: TEST_HOSTEL_CODE } });
    }
  });
  cy.intercept("GET", `${API}/auth/me/`, (req) =>
    req.reply(opts.unauthenticated ? { statusCode: 401, body: { detail: "auth required" } } : { statusCode: 200, body: TEST_USER })
  );
  cy.intercept("POST", `${API}/auth/token/refresh/`, { statusCode: opts.unauthenticated ? 401 : 200, body: {} });
  cy.intercept("POST", `${API}/auth/logout/`, { statusCode: 204 });
  // Generic envelope for every other read.
  cy.intercept("GET", `${API}/**`, { statusCode: 200, body: { success: true, data: { results: [], count: 0 }, meta: {} } });
});

Cypress.Commands.add("seedSession", () => {
  cy.window().then((win) => {
    win.localStorage.setItem("session_active", "1");
    win.localStorage.setItem("hostel_code", TEST_HOSTEL_CODE);
    win.localStorage.setItem("role", "WARDEN");
  });
});

Cypress.Commands.add("login", () => {
  cy.mockApi();
  cy.visit("/login");
  cy.findByLabelText("Hostel ID").type(TEST_HOSTEL_CODE);
  cy.findByLabelText("Username").type("warden");
  cy.findByLabelText("Password").type("TestPass!234");
  cy.contains("button", "Login").click();
  cy.url().should("include", "/dashboard");
});
