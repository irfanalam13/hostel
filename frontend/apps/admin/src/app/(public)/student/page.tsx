import { redirect } from "next/navigation";

/**
 * Legacy student portal login URL. Students/residents now sign in through the
 * single unified tenant login at `/login`; the backend routes them to
 * `/student/dashboard` afterwards. Kept as a redirect for backward compat.
 * (Note: `/student/dashboard` and other `/student/*` app routes are unaffected
 * — only the bare `/student` login page redirects.)
 */
export default function StudentLoginPage() {
  redirect("/login");
}
