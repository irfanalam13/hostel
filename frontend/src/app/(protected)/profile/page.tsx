"use client";

import { useEffect, useState } from "react";
import { authApi, type AuthUser } from "@/features/auth/api/auth.api";
import { authStore } from "@/shared/auth/auth.store";
import { Topbar } from "@/shared/ui/Topbar";

export default function ProfilePage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    authApi
      .me()
      .then(setUser)
      .catch((err: any) => setMessage(err?.message || "Failed to load profile."));
  }, []);

  return (
    <div>
      <Topbar title="Profile" />
      {message ? <div className="mb-3 text-sm text-red-600">{message}</div> : null}

      <div className="rounded-2xl border bg-white p-4 text-sm">
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <div className="text-zinc-500">Username</div>
            <div className="font-medium">{user?.username || "-"}</div>
          </div>
          <div>
            <div className="text-zinc-500">Email</div>
            <div className="font-medium">{user?.email || "-"}</div>
          </div>
          <div>
            <div className="text-zinc-500">Role</div>
            <div className="font-medium">{user?.role || "-"}</div>
          </div>
          <div>
            <div className="text-zinc-500">Hostel ID</div>
            <div className="font-mono">{authStore.getHostelCode() || "-"}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
