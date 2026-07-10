import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ErrorBoundary } from "../ErrorBoundary";

// Capture monitoring calls without hitting the real logger.
vi.mock("@hostel/utils", () => ({
  captureError: vi.fn(),
}));
import { captureError } from "@hostel/utils";

function Boom({ explode }: { explode: boolean }) {
  if (explode) throw new Error("kaboom");
  return <div>safe content</div>;
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Silence React's expected error console output for the thrown render.
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <div>hello</div>
      </ErrorBoundary>
    );
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("renders the fallback and reports to monitoring when a child throws", () => {
    render(
      <ErrorBoundary boundary="test">
        <Boom explode />
      </ErrorBoundary>
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
    expect(captureError).toHaveBeenCalledTimes(1);
  });

  it("recovers via Retry once the child stops throwing", async () => {
    const user = userEvent.setup();
    function Wrapper() {
      // After reset, the boundary re-renders children; render a safe child then.
      return (
        <ErrorBoundary>
          <Boom explode={false} />
        </ErrorBoundary>
      );
    }
    // First mount with a throwing tree.
    const { rerender } = render(
      <ErrorBoundary>
        <Boom explode />
      </ErrorBoundary>
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await user.click(screen.getByText("Retry"));
    // Replace with a non-throwing subtree and confirm normal content shows.
    rerender(<Wrapper />);
    expect(screen.getByText("safe content")).toBeInTheDocument();
  });
});
