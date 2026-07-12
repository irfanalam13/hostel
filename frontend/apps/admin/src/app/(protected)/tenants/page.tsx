import Link from "next/link";

export default function TenantsHomePage() {
  const cards = [
    { href: "/tenants/plans", title: "Plans", desc: "View available plans" },
    { href: "/tenants/hostels", title: "Hostels", desc: "Create & manage hostels" },
    { href: "/tenants/subscriptions", title: "Subscriptions", desc: "Manage subscriptions (auth)" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Tenants</h1>

      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className="rounded-2xl border border-zinc-200 bg-white p-4 hover:bg-zinc-50"
          >
            <div className="font-semibold">{c.title}</div>
            <div className="mt-1 text-sm text-zinc-600">{c.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}