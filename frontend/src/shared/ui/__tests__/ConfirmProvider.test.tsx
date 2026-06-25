import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmProvider, useConfirm } from "@/shared/ui/ConfirmProvider";

function Harness({ onResult }: { onResult: (v: boolean) => void }) {
  const confirm = useConfirm();
  return (
    <button
      onClick={async () => {
        const ok = await confirm({ title: "Delete", message: "Sure?", confirmText: "Yes" });
        onResult(ok);
      }}
    >
      trigger
    </button>
  );
}

describe("ConfirmProvider / useConfirm", () => {
  it("resolves true when confirmed", async () => {
    const user = userEvent.setup();
    let result: boolean | undefined;
    render(
      <ConfirmProvider>
        <Harness onResult={(v) => (result = v)} />
      </ConfirmProvider>
    );
    await user.click(screen.getByText("trigger"));
    expect(screen.getByText("Sure?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yes" }));
    expect(result).toBe(true);
    expect(screen.queryByText("Sure?")).not.toBeInTheDocument();
  });

  it("resolves false when cancelled", async () => {
    const user = userEvent.setup();
    let result: boolean | undefined;
    render(
      <ConfirmProvider>
        <Harness onResult={(v) => (result = v)} />
      </ConfirmProvider>
    );
    await user.click(screen.getByText("trigger"));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(result).toBe(false);
  });
});
