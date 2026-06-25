import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToastProvider, useToast } from "@/shared/ui/toast/ToastProvider";

function Harness() {
  const toast = useToast();
  return (
    <div>
      <button onClick={() => toast.success("Saved!", "Done")}>ok</button>
      <button onClick={() => toast.error("Boom")}>err</button>
    </div>
  );
}

function setup() {
  return render(
    <ToastProvider>
      <Harness />
    </ToastProvider>
  );
}

describe("ToastProvider / useToast", () => {
  it("shows a success toast with title and message", async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByText("ok"));
    expect(screen.getByText("Done")).toBeInTheDocument();
    expect(screen.getByText("Saved!")).toBeInTheDocument();
  });

  it("renders an error toast with role=alert", async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByText("err"));
    expect(screen.getByRole("alert")).toHaveTextContent("Boom");
  });

  it("dismisses a toast when the close button is clicked", async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByText("err"));
    expect(screen.getByText("Boom")).toBeInTheDocument();
    await user.click(screen.getByLabelText("Dismiss notification"));
    expect(screen.queryByText("Boom")).not.toBeInTheDocument();
  });

  it("throws if useToast is used without a provider", () => {
    function Bare() {
      useToast();
      return null;
    }
    // Suppress React's error logging for this expected throw.
    expect(() => act(() => render(<Bare />) as unknown as void)).toThrow(
      /useToast must be used within/
    );
  });
});
