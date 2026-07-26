import Link from "next/link";

export default function NotFound() {
  return (
    <div className="grid min-h-[70vh] place-items-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
        <div className="text-5xl font-bold text-zinc-300">404</div>
        <h1 className="mt-2 text-lg font-semibold text-zinc-900">Page not found</h1>
        <p className="mt-1 text-sm text-zinc-500">
          The page you’re looking for doesn’t exist or may have moved.
        </p>
        <Link
          href="/dashboard"
          className="mt-6 inline-block rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
