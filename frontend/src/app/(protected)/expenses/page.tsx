"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthed } from "@/shared/lib/auth";
import { Topbar } from "@/shared/ui/Topbar";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Modal } from "@/shared/ui/Modal";
import { Table } from "@/shared/ui/Table";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import { useConfirm } from "@/shared/ui/ConfirmProvider";
import { addExpense, deleteExpense, loadState, updateExpense } from "@/features/hostels/store";
import type { Expense, ExpenseCategory } from "@/features/hostels/types";
import { isoToday, ymToday } from "@/shared/lib/dates";
import { sumExpenses } from "@/shared/lib/finance";

const categories: ExpenseCategory[] = ["Food","Electricity","Water","Internet","Repair","Salary","Other"];

export default function ExpensesPage() {
  const router = useRouter();
  const toast = useToast();
  const confirm = useConfirm();
  const [tick, setTick] = useState(0);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);

  const [month, setMonth] = useState(ymToday());
  const [date, setDate] = useState(isoToday());
  const [category, setCategory] = useState<ExpenseCategory>("Other");
  const [amount, setAmount] = useState<number>(0);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!isAuthed()) router.replace("/login");
  }, [router]);

  const state = useMemo(() => loadState(), [tick]);
  const expenses = state.expenses.filter(e => e.date.startsWith(month));
  const total = sumExpenses(state.expenses, month);

  function resetForm() {
    setDate(isoToday());
    setCategory("Other");
    setAmount(0);
    setNote("");
  }

  function openAdd() {
    setEditing(null);
    resetForm();
    setOpen(true);
  }

  function openEdit(e: Expense) {
    setEditing(e);
    setDate(e.date);
    setCategory(e.category);
    setAmount(e.amount);
    setNote(e.note ?? "");
    setOpen(true);
  }

  function save() {
    if (amount <= 0) return toast.warning("Amount must be greater than 0.");
    if (!date) return toast.warning("Date is required.");

    if (!editing) {
      addExpense({ date, category, amount, note });
      toast.success("Expense added.");
    } else {
      updateExpense(editing.id, { date, category, amount, note });
      toast.success("Expense updated.");
    }
    setOpen(false);
    setTick(t => t + 1);
  }

  async function remove(id: string) {
    const ok = await confirm({
      title: "Delete expense",
      message: "Delete this expense? This can’t be undone.",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    deleteExpense(id);
    toast.success("Expense deleted.");
    setTick(t => t + 1);
  }

  return (
    <div>
      <Topbar />

      <div className="flex flex-wrap gap-2 justify-between items-end mb-3">
        <div>
          <div className="text-lg font-semibold">Expenses (Spent)</div>
          <div className="text-sm text-gray-600">Total for {month}: <b>{total}</b></div>
        </div>

        <div className="flex gap-2 items-end">
          <Input label="Month (YYYY-MM)" value={month} onChange={(e) => setMonth(e.target.value)} />
          <Button onClick={openAdd}>Add Expense</Button>
        </div>
      </div>

      <Table>
        <thead>
          <tr className="text-left border-b border-gray-200">
            <th className="p-3">Date</th>
            <th className="p-3">Category</th>
            <th className="p-3">Amount</th>
            <th className="p-3">Note</th>
            <th className="p-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {expenses.map(e => (
            <tr key={e.id} className="border-b border-gray-100">
              <td className="p-3">{e.date}</td>
              <td className="p-3">{e.category}</td>
              <td className="p-3">{e.amount}</td>
              <td className="p-3">{e.note ?? "-"}</td>
              <td className="p-3 flex gap-2">
                <Button variant="ghost" onClick={() => openEdit(e)}>Edit</Button>
                <Button variant="danger" onClick={() => remove(e.id)}>Delete</Button>
              </td>
            </tr>
          ))}
          {expenses.length === 0 ? (
            <tr><td className="p-4 text-gray-500" colSpan={5}>No expenses for this month.</td></tr>
          ) : null}
        </tbody>
      </Table>

      <Modal open={open} title={editing ? "Edit Expense" : "Add Expense"} onClose={() => setOpen(false)}>
        <div className="grid gap-3">
          <Input label="Date" value={date} onChange={(e) => setDate(e.target.value)} />
          <label className="block">
            <div className="text-sm mb-1 text-gray-700">Category</div>
            <select
              className="w-full px-3 py-2 rounded-lg border border-gray-200"
              value={category}
              onChange={(e) => setCategory(e.target.value as any)}
            >
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <Input label="Amount" type="number" value={String(amount)} onChange={(e) => setAmount(Number(e.target.value))} />
          <Input label="Note" value={note} onChange={(e) => setNote(e.target.value)} />

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={save}>Save</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}