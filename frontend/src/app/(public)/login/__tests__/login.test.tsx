import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), prefetch: vi.fn() }),
}));

const apiFetch = vi.fn();
vi.mock("@/shared/api/apiClient", () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }));

import LoginPage from "@/app/(public)/login/page";
import { ToastProvider } from "@/shared/ui/toast/ToastProvider";
import { AuthProvider } from "@/shared/auth/AuthProvider";

function renderLogin() {
  return render(
    <ToastProvider>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </ToastProvider>
  );
}

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  fireEvent.change(screen.getByLabelText("Hostel ID"), { target: { value: "HTL-ABC12345" } });
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "warden" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
  await user.click(screen.getByRole("button", { name: /login/i }));
}

describe("Login flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // AuthProvider mounts and calls /auth/me; no session marker -> not called,
    // but be safe and default any call to a rejection.
    apiFetch.mockRejectedValue(new Error("401"));
  });

  it("logs in, shows a success toast and redirects to the dashboard", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation((path: string) => {
      if (path === "/auth/login/") {
        return Promise.resolve({ detail: "ok", hostel_code: "HTL-ABC12345", user: { role: "WARDEN" } });
      }
      return Promise.reject(new Error("401")); // /auth/me
    });
    renderLogin();
    await fillAndSubmit(user);

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith(
      "/auth/login/",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ hostel_id: "HTL-ABC12345", username: "warden", password: "secret123" }),
      })
    ));
    expect(await screen.findByText("Login successful")).toBeInTheDocument();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows an error toast and stays on the page on bad credentials", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation((path: string) => {
      if (path === "/auth/login/") {
        const err = new Error("Invalid credentials") as Error & { data?: unknown };
        err.data = { detail: "Invalid credentials" };
        return Promise.reject(err);
      }
      return Promise.reject(new Error("401"));
    });
    renderLogin();
    await fillAndSubmit(user);

    expect(await screen.findByText("Login failed")).toBeInTheDocument();
    expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalledWith("/dashboard");
  });

  it("validates required fields before calling the API", async () => {
    const user = userEvent.setup();
    renderLogin();
    // Submit with everything empty.
    await user.click(screen.getByRole("button", { name: /login/i }));
    expect(apiFetch).not.toHaveBeenCalledWith("/auth/login/", expect.anything());
  });
});
