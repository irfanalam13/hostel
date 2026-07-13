import { redirect } from "next/navigation";

/**
 * Legacy staff portal URL. Role-specific login pages have been collapsed into
 * the single unified tenant login at `/login`; this path is kept only so old
 * bookmarks/links keep working.
 */
export default function StaffLoginPage() {
  redirect("/login");
}
