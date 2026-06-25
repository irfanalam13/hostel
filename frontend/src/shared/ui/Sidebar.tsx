"use client";

import Link from "next/link";

const links = [
  { name: "Dashboard", href: "/dashboard" },
  { name: "Students", href: "/students" },
  { name: "Residents", href: "/residents" },
  { name: "Rooms", href: "/rooms" },
  { name: "Fees", href: "/fees" },
  { name: "Payments", href: "/payments" },
  { name: "Attendance", href: "/attendance" },
  { name: "Billing", href: "/billing" },
  { name: "Reports", href: "/reports" },
  { name: "Exports", href: "/exports" },
  { name: "Backups", href: "/backups" },
  { name: "Tenants", href: "/tenants" },
];

export default function Sidebar() {
  return (
    <div className="w-64 bg-white shadow-md p-4">
      <h2 className="text-xl font-bold mb-6">Hostel System</h2>
      <ul className="space-y-2">
        {links.map((link) => (
          <li key={link.name}>
            <Link
              href={link.href}
              className="block p-2 rounded hover:bg-gray-100"
            >
              {link.name}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}