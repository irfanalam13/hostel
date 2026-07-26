import { redirect } from "next/navigation";

/**
 * Legacy parent portal login URL. Parents/guardians now sign in through the
 * single unified tenant login at `/login`; the backend routes them to
 * `/parent/dashboard` afterwards. Kept as a redirect for backward compat.
 * (`/parent/dashboard` and other `/parent/*` app routes are unaffected.)
 */
export default function ParentLoginPage() {
  redirect("/login");
}
