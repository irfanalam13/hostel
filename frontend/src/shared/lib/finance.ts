import type { Student, Payment, Expense, Room, Bed } from "@/features/hostels/types";
import { inMonth } from "./dates";

export function sumPayments(payments: Payment[], ym: string, onlyToday = false) {
  const today = new Date().toISOString().slice(0, 10);
  return payments
    .filter(p => inMonth(p.date, ym))
    .filter(p => (onlyToday ? p.date === today : true))
    .reduce((acc, p) => acc + p.amount, 0);
}

export function sumExpenses(expenses: Expense[], ym: string) {
  return expenses
    .filter(e => inMonth(e.date, ym))
    .reduce((acc, e) => acc + e.amount, 0);
}

export function computeDues(students: Student[], payments: Payment[], ym: string) {
  const paidByStudent: Record<string, number> = {};
  for (const p of payments.filter(p => inMonth(p.date, ym))) {
    paidByStudent[p.studentId] = (paidByStudent[p.studentId] ?? 0) + p.amount;
  }

  const dues = students.map(s => {
    const paid = paidByStudent[s.id] ?? 0;
    const due = Math.max(0, s.monthlyFee - paid);
    return { studentId: s.id, name: s.fullName, monthlyFee: s.monthlyFee, paid, due };
  });

  const totalDue = dues.reduce((a, d) => a + d.due, 0);
  const studentsDue = dues.filter(d => d.due > 0).length;

  return { dues, totalDue, studentsDue };
}

export function occupancy(students: Student[], rooms: Room[], beds: Bed[]) {
  const active = students.filter(s => s.status === "active");
  const occupiedBedIds = new Set(active.map(s => s.bedId).filter(Boolean) as string[]);
  const occupied = occupiedBedIds.size;
  const totalBeds = beds.length;
  const available = Math.max(0, totalBeds - occupied);

  // room wise
  const byRoom = rooms.map(r => {
    const roomBeds = beds.filter(b => b.roomId === r.id);
    const roomOcc = roomBeds.filter(b => occupiedBedIds.has(b.id)).length;
    return { room: r.label, totalBeds: roomBeds.length, occupied: roomOcc, available: roomBeds.length - roomOcc };
  });

  return { totalBeds, occupied, available, byRoom };
}

export function dailyCollections(payments: Payment[], dateISO: string) {
  return payments.filter(p => p.date === dateISO).reduce((a, p) => a + p.amount, 0);
}