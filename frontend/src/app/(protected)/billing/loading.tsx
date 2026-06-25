import { StatCardsSkeleton, TableSkeleton, Skeleton } from "@/shared/ui/Skeleton";

export default function BillingLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-28" />
      <StatCardsSkeleton count={4} />
      <TableSkeleton cols={5} />
    </div>
  );
}
