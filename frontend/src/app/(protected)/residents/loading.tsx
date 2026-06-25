import { TableSkeleton, Skeleton } from "@/shared/ui/Skeleton";

export default function ResidentsLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-20 w-full rounded-2xl" />
      <TableSkeleton cols={4} />
    </div>
  );
}
