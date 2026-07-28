"use client";

import { useState } from "react";
import { Button } from "@hostel/ui";
import { loadMoreDirectoryHostels, type DirectoryHostel } from "./api";
import { HostelCard } from "./HostelCard";

export function LoadMoreButton({ initialNext }: { initialNext: string }) {
  const [items, setItems] = useState<DirectoryHostel[]>([]);
  const [next, setNext] = useState<string | null>(initialNext);
  const [loading, setLoading] = useState(false);

  async function loadMore() {
    if (!next || loading) return;
    setLoading(true);
    try {
      const page = await loadMoreDirectoryHostels(next);
      setItems((prev) => [...prev, ...page.items]);
      setNext(page.next);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {items.length > 0 && (
        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((hostel) => (
            <HostelCard key={hostel.workspace} hostel={hostel} />
          ))}
        </div>
      )}
      {next && (
        <div className="mt-8 flex justify-center">
          <Button variant="secondary" onClick={loadMore} loading={loading}>
            Load more hostels
          </Button>
        </div>
      )}
    </>
  );
}
