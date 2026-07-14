"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@hostel/api";
import { generateMonth, getLedgers } from "@/features/fees/api/fee-ledger.api";
import type { FeeLedger } from "@/features/fees/types/fee-ledger.types";
import { Topbar } from "@/components/shell/Topbar";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";

type FeePlan = {
  id: number;
  name: string;
  monthly_amount: string;
  is_active: boolean;
};

export default function FeesPage() {
  const [plans, setPlans] = useState<FeePlan[]>([]);
  const [ledgers, setLedgers] = useState<FeeLedger[]>([]);
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    const [planRes, ledgerRows] = await Promise.all([
      api.get<FeePlan[]>("/fees/fee-plans/"),
      getLedgers({ month }),
    ]);
    setPlans(planRes.data);
    setLedgers(ledgerRows);
  }, [month]);

  useEffect(() => {
    refresh().catch((err) => setMessage(err?.message || "Failed to load fees."));
  }, [refresh]);

  async function savePlan(e: React.FormEvent) {
    e.preventDefault();
    await api.post<FeePlan>("/fees/fee-plans/", {
      name,
      monthly_amount: amount,
      is_active: true,
    });
    setName("");
    setAmount("");
    await refresh();
  }

  async function runGenerate() {
    const result = await generateMonth(month);
    setMessage(`Generated ${result.created} ledger row(s) for ${result.month}.`);
    await refresh();
  }

  return (
    <div>
      <Topbar title="Fees" />
      {message ? <div className="mb-3 text-sm text-zinc-700">{message}</div> : null}

      <div className="grid gap-4 md:grid-cols-2 mb-4">
        <form onSubmit={savePlan} className="rounded-2xl border bg-white p-4 space-y-3">
          <div className="font-semibold">Fee Plan</div>
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <Input label="Monthly Amount" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          <Button type="submit">Save Plan</Button>
        </form>

        <div className="rounded-2xl border bg-white p-4 space-y-3">
          <div className="font-semibold">Monthly Ledger</div>
          <Input label="Month" value={month} onChange={(e) => setMonth(e.target.value)} />
          <Button type="button" onClick={runGenerate}>
            Generate Month
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Table>
          <thead>
            <tr className="text-left border-b">
              <th className="p-3">Plan</th>
              <th className="p-3">Amount</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((plan) => (
              <tr key={plan.id} className="border-b">
                <td className="p-3">{plan.name}</td>
                <td className="p-3">{plan.monthly_amount}</td>
              </tr>
            ))}
          </tbody>
        </Table>

        <Table>
          <thead>
            <tr className="text-left border-b">
              <th className="p-3">Student</th>
              <th className="p-3">Due</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {ledgers.map((ledger) => (
              <tr key={ledger.id} className="border-b">
                <td className="p-3">#{ledger.student}</td>
                <td className="p-3">{ledger.net_due}</td>
                <td className="p-3">{ledger.status}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  );
}
