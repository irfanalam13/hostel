/**
 * Authenticated navigation smoke (Cypress).
 *
 * Seeds a session, mocks reads, and walks the core routes asserting each renders
 * without being bounced to /login or throwing an uncaught error.
 */
const ROUTES = ["/dashboard", "/residents", "/payments", "/attendance", "/complaints", "/reports", "/settings", "/sync"];

describe("Authenticated navigation smoke", () => {
  beforeEach(() => {
    cy.mockApi();
    cy.visit("/login"); // establishes window for seedSession
    cy.seedSession();
  });

  ROUTES.forEach((route) => {
    it(`renders ${route}`, () => {
      cy.visit(route);
      cy.url().should("include", route);
      cy.get("body").should("be.visible");
    });
  });
});
