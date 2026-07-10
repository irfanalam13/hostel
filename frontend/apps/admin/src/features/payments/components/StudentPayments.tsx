"use client";

import { useEffect, useState } from "react";
import { getPayments } from "../api/payment.api";
import type { Payment } from "../types/payment.types";
import StudentPaymentForm from "./StudentPaymentForm";

export default function StudentPayments({ studentId }: { studentId: string }) {
  const [payments, setPayments] = useState<Payment[]>([]);

  const refresh = () =>
    getPayments({ student: studentId, ordering: "-date" })
      .then(setPayments)
      .catch(() => setPayments([]));

  useEffect(() => {
    refresh();
  }, [studentId]);

  return (
    <div className="mt-4">
      <StudentPaymentForm studentId={studentId} onCreated={refresh} />

      <div className="border rounded p-4 mt-4">
        <div className="font-semibold mb-2">Payment History</div>

        {payments.length === 0 ? (
          <div className="text-sm text-gray-600">No payments yet.</div>
        ) : (
          <div className="space-y-2">
            {payments.map((payment) => (
              <div key={payment.id} className="border rounded p-3 text-sm">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                  <div>
                    <div className="font-semibold">Rs {payment.amount}</div>
                    <div className="text-gray-600">
                      {payment.date} / {payment.method} / Ref: {payment.reference_no || "-"}
                    </div>
                  </div>

                  <div className="text-gray-700">
                    Receipt:{" "}
                    <span className="font-semibold">{payment.receipt?.receipt_no ?? "-"}</span>
                  </div>
                </div>

                <div className="mt-2 text-xs text-gray-600">
                  Allocations: {payment.allocations?.length ?? 0}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
