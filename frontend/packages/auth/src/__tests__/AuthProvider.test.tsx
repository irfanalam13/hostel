import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), prefetch: vi.fn() }),
}));

const apiFetch = vi.fn();
vi.mock("@hostel/api", () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }));

import { AuthProvider, useAuth } from "../AuthProvider";
import { authStore } from "../auth.store";

function StatusProbe() {
  const { status, user } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.username ?? "none"}</span>
    </div>
  );
}

function renderAuth() {
  return render(
    <AuthProvider>
      <StatusProbe />
    </AuthProvider>
  );
}

describe("AuthProvider (route protection / session)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("is unauthenticated and skips the network call when there is no session marker", async () => {
    renderAuth();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("validates an existing session via /auth/me and becomes authenticated", async () => {
    authStore.setAuthed();
    apiFetch.mockResolvedValueOnce({ id: 1, username: "warden", role: "WARDEN" });
    renderAuth();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("user")).toHaveTextContent("warden");
    expect(apiFetch).toHaveBeenCalledWith("/auth/me/", expect.objectContaining({ method: "GET" }));
  });

  it("drops to unauthenticated when /auth/me rejects (expired session)", async () => {
    authStore.setAuthed();
    apiFetch.mockRejectedValueOnce(new Error("401"));
    renderAuth();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated"));
    // Marker cleared so guards won't loop.
    expect(authStore.getAccess()).toBeNull();
  });
});
