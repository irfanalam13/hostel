import { redirect } from "next/navigation";

// The admin zone has no landing page of its own — the marketing site (client
// zone) owns "/" on the public origin. This root route only exists for direct
// access to the admin app (dev on :3001, container healthchecks).
export default function AdminIndex() {
  redirect("/dashboard");
}
