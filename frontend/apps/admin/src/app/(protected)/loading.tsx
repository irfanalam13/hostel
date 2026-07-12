import { PageSkeleton } from "@hostel/ui";

// Shown during navigation into any protected route segment that doesn't define
// its own loading UI — prevents a blank screen mid-transition.
export default function Loading() {
  return (
    <div className="p-1">
      <PageSkeleton />
    </div>
  );
}
