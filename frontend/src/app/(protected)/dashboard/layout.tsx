// Auth is enforced by the parent (protected) layout via AuthProvider. The old
// version here read a legacy `access_token` from localStorage — which no longer
// exists (tokens are httpOnly cookies), so it redirected even valid sessions to
// /login. This layout is now a simple pass-through.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
