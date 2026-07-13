import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), prefetch: vi.fn() }),
}));

const apiFetch = vi.fn();
vi.mock("@hostel/api", () => ({
  apiFetch: (...a: unknown[]) => apiFetch(...a),
  // Workspace-level failures aren't exercised here (jsdom host is localhost,
  // so no workspace is resolved and no branding fetch happens).
  isWorkspaceError: () => false,
}));

import LoginPage from "@/app/(public)/login/page";
import { ToastProvider } from "@hostel/ui";
import { AuthProvider } from "@hostel/auth";

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
  fireEvent.change(screen.getByLabelText("Username or email"), { target: { value: "warden" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
  await user.click(screen.getByRole("button", { name: /sign in/i }));
}

describe("Login flow (unified tenant login, legacy Hostel-ID path)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // AuthProvider mounts and calls /auth/me; no session marker -> not called,
    // but be safe and default any call to a rejection.
    apiFetch.mockRejectedValue(new Error("401"));
  });

  it("logs in with NO portal (unified: all roles) and follows the backend redirect", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation((path: string) => {
      if (path === "/auth/login/") {
        return Promise.resolve({
          detail: "ok",
          hostel_code: "HTL-ABC12345",
          user: { role: "WARDEN" },
          role: "WARDEN",
          redirect: "/dashboard",
        });
      }
      return Promise.reject(new Error("401")); // /auth/me
    });
    renderLogin();
    await fillAndSubmit(user);

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/auth/login/", expect.anything()));
    const [, options] = apiFetch.mock.calls.find(([p]) => p === "/auth/login/")!;
    const body = JSON.parse((options as { body: string }).body);
    // The unified login sends NO portal — the backend admits every role and
    // routes by role. (Role-specific portals were collapsed in Phase 7.)
    expect(body).toEqual({
      username: "warden",
      password: "secret123",
      remember: false,
      hostel_id: "HTL-ABC12345",
    });
    expect(body).not.toHaveProperty("portal");
    expect(await screen.findByText("Login successful")).toBeInTheDocument();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows an error and stays on the page on bad credentials", async () => {
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
    // Shown both inline and in the toast.
    expect(screen.getAllByText("Invalid credentials").length).toBeGreaterThan(0);
    expect(replace).not.toHaveBeenCalledWith("/dashboard");
  });

  it("validates required fields before calling the API", async () => {
    const user = userEvent.setup();
    renderLogin();
    // Submit with everything empty — native `required` + JS validation both
    // stop the request before any API call.
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(apiFetch).not.toHaveBeenCalledWith("/auth/login/", expect.anything());
  });

  it("offers remember-me and passes it through", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation((path: string) =>
      path === "/auth/login/"
        ? Promise.resolve({ hostel_code: "HTL-ABC12345", user: { role: "WARDEN" }, redirect: "/dashboard" })
        : Promise.reject(new Error("401")),
    );
    renderLogin();
    await user.click(screen.getByLabelText(/keep me signed in/i));
    await fillAndSubmit(user);

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/auth/login/", expect.anything()));
    const [, options] = apiFetch.mock.calls.find(([p]) => p === "/auth/login/")!;
    expect(JSON.parse((options as { body: string }).body).remember).toBe(true);
  });
});
