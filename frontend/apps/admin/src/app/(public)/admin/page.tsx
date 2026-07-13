import { redirect } from "next/navigation";

/**
 * Legacy admin login URL. Owners and hostel admins now sign in through the
 * single unified tenant login at `/login` (authentication decides identity,
 * authorization decides access). Kept as a redirect for backward compatibility.
 */
export default function AdminLoginPage() {
  redirect("/login");
}
