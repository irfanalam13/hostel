import "@testing-library/cypress/add-commands";
import "./commands";

// Don't let an unrelated third-party/ResizeObserver console error fail a run.
Cypress.on("uncaught:exception", (err) => {
  if (/ResizeObserver|Hydration|hydrat/i.test(err.message)) return false;
  return true;
});
