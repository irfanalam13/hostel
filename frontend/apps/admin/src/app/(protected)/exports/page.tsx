"use client";

import { apiDownload } from "@hostel/api";
import { Topbar } from "@/components/shell/Topbar";
import { Button } from "@hostel/ui";

export default function ExportsPage() {
  return (
    <div>
      <Topbar title="Exports" />

      <div className="rounded-2xl border bg-white p-4 flex flex-wrap gap-3">
        <Button onClick={() => apiDownload("/exports/residents.csv")}>Residents CSV</Button>
        <Button onClick={() => apiDownload("/exports/invoices.csv")}>Invoices CSV</Button>
        <Button onClick={() => apiDownload("/exports/ledger.csv")}>Ledger CSV</Button>
        <Button onClick={() => apiDownload("/exports/occupancy.csv")}>Occupancy CSV</Button>
        <Button onClick={() => apiDownload("/exports/dues.csv")}>Due Payments CSV</Button>
        <Button onClick={() => apiDownload("/exports/collections.csv")}>Collections CSV</Button>
        <Button onClick={() => apiDownload("/exports/complaints.csv")}>Complaints CSV</Button>
        <Button onClick={() => apiDownload("/exports/attendance-leave.csv")}>Attendance/Leave CSV</Button>
        <Button onClick={() => apiDownload("/exports/visitors.csv")}>Visitors CSV</Button>
        <Button onClick={() => apiDownload("/exports/entry-exit.csv")}>Entry/Exit CSV</Button>
      </div>
    </div>
  );
}
