import { EmptyState } from "@hostel/ui";
import type { DirectoryHostel } from "./api";
import { HostelCard } from "./HostelCard";
import { LoadMoreButton } from "./LoadMoreButton";

export function HostelGrid({
  hostels,
  next,
}: {
  hostels: DirectoryHostel[];
  next: string | null;
}) {
  if (hostels.length === 0) {
    return (
      <EmptyState
        icon="🔍"
        title="No hostels match your filters"
        description="Try widening your search — a different city, a lower rating floor, or fewer amenity filters."
      />
    );
  }

  return (
    <div>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {hostels.map((hostel) => (
          <HostelCard key={hostel.workspace} hostel={hostel} />
        ))}
      </div>
      {next && <LoadMoreButton initialNext={next} />}
    </div>
  );
}
