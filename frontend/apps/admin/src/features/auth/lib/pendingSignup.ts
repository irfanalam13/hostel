import type { SignupPayload } from "@/features/auth/api/auth.api";

// The signup form is split across two pages: the details page collects
// everything and requests an email OTP, then hands off to the verification
// page which supplies that OTP to actually create the account. We stash the
// in-progress form here so the second page can complete it.
//
// Deliberately sessionStorage (not the localStorage `storage` helper): this is
// short-lived, per-tab, and cleared as soon as the account is created — it must
// never outlive the signup handoff. The password lives here only for those few
// seconds between the two pages.
const KEY = "pending_signup";

/** Everything the signup endpoint needs except the OTP (added on verify). */
export type PendingSignup = Omit<SignupPayload, "otp">;

export function savePendingSignup(data: PendingSignup): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    // storage full/unavailable — the verify page will bounce back to /signup.
  }
}

export function loadPendingSignup(): PendingSignup | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as PendingSignup) : null;
  } catch {
    return null;
  }
}

export function clearPendingSignup(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
