"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSidebar } from "@/shared/providers/SidebarContext";
import { LayoutDashboard, Users, CreditCard, Home, Menu } from "lucide-react";

export function MobileBottomNav() {
  const pathname = usePathname();
  const { toggleMobileSidebar } = useSidebar();

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Students", href: "/students", icon: Users },
    { name: "Payments", href: "/payments", icon: CreditCard },
    { name: "Rooms", href: "/rooms", icon: Home },
  ];

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 h-[64px] bg-[color-mix(in_srgb,var(--card)_94%,transparent)] border-t border-[var(--border)] backdrop-blur-md flex items-center justify-around px-4 z-40 pb-safe shadow-[var(--shadow-sm)] select-none">
      {navItems.map((item) => {
        const isActive = pathname === item.href;
        const Icon = item.icon;

        return (
          <Link
            key={item.name}
            href={item.href}
            className={`flex flex-col items-center justify-center flex-1 h-full py-1 text-[10px] font-semibold transition ${
              isActive ? "text-[var(--accent)]" : "text-[var(--muted)] hover:text-[var(--foreground-secondary)]"
            }`}
          >
            <Icon className={`w-5.5 h-5.5 mb-1 transition-transform ${isActive ? "scale-105" : ""}`} />
            <span>{item.name}</span>
          </Link>
        );
      })}

      {/* "More" button triggers mobile sidebar drawer */}
      <button
        onClick={toggleMobileSidebar}
        className="flex flex-col items-center justify-center flex-1 h-full py-1 text-[10px] font-semibold text-[var(--muted)] hover:text-[var(--foreground-secondary)]"
      >
        <Menu className="w-5.5 h-5.5 mb-1" />
        <span>More</span>
      </button>
    </nav>
  );
}
