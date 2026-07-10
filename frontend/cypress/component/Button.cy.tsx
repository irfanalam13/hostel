/**
 * Component test (Cypress) — the shared Button primitive.
 *
 * Demonstrates the component-testing harness and locks in the loading/disabled
 * behaviour that Audit H5 added (no double-submits, in-flight feedback).
 */
import { Button } from "@hostel/ui";

describe("<Button />", () => {
  it("renders its label and handles clicks", () => {
    const onClick = cy.stub().as("onClick");
    cy.mount(<Button onClick={onClick}>Save</Button>);
    cy.contains("button", "Save").click();
    cy.get("@onClick").should("have.been.calledOnce");
  });

  it("is non-interactive while loading", () => {
    const onClick = cy.stub().as("onClick");
    cy.mount(
      <Button loading onClick={onClick}>
        Save
      </Button>
    );
    cy.get("button").should("be.disabled");
    cy.get("button").click({ force: true });
    cy.get("@onClick").should("not.have.been.called");
  });
});
