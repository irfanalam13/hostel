import { StatCardsSkeleton, Skeleton } from "@hostel/ui";

export default function DashboardLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-40" />
      <StatCardsSkeleton count={3} />
      <StatCardsSkeleton count={3} />
    </div>
  );
}
