import { lsGet, lsSet, uid } from "@hostel/utils";
import type {
  HostelState,
  Student,
  Expense,
  Payment,
  Room,
  Bed,
  Settings,
  AuditAction,
} from "./types";

const KEY = "hm_state_v2";

function nowISO() {
  return new Date().toISOString();
}

const DEFAULT_STATE: HostelState = {
  settings: { hostelName: "My Hostel", totalBeds: 20 },

  rooms: [],
  beds: [],

  students: [],
  expenses: [],
  payments: [],

  audit: [],
};

export function loadState(): HostelState {
  return lsGet<HostelState>(KEY, DEFAULT_STATE);
}

export function saveState(state: HostelState) {
  lsSet(KEY, state);
}

function log(state: HostelState, action: AuditAction, message: string) {
  state.audit.unshift({ id: uid("log"), at: nowISO(), action, message });
}

// ---------- Settings ----------
export function updateSettings(patch: Partial<Settings>) {
  const state = loadState();
  state.settings = { ...state.settings, ...patch };
  log(state, "SETTINGS_UPDATED", `Settings updated`);
  saveState(state);
}

// ---------- Rooms ----------
export function addRoom(payload: Omit<Room, "id">) {
  const state = loadState();
  const room: Room = { ...payload, id: uid("room") };
  state.rooms.unshift(room);
  log(state, "ROOM_CREATED", `Room created: ${room.label}`);
  saveState(state);
  return room;
}

export function updateRoom(id: string, patch: Partial<Room>) {
  const state = loadState();
  state.rooms = state.rooms.map(r => (r.id === id ? { ...r, ...patch } : r));
  log(state, "ROOM_UPDATED", `Room updated`);
  saveState(state);
}

// ---------- Beds ----------
export function addBed(payload: Omit<Bed, "id">) {
  const state = loadState();
  const bed: Bed = { ...payload, id: uid("bed") };
  state.beds.unshift(bed);
  log(state, "BED_CREATED", `Bed created: ${bed.label}`);
  saveState(state);
  return bed;
}

export function updateBed(id: string, patch: Partial<Bed>) {
  const state = loadState();
  state.beds = state.beds.map(b => (b.id === id ? { ...b, ...patch } : b));
  log(state, "BED_UPDATED", `Bed updated`);
  saveState(state);
}

// Assign bed to student (and ensure single occupancy)
export function assignBed(studentId: string, roomId: string, bedId: string) {
  const state = loadState();

  // unassign this bed from any other active student
  state.students = state.students.map(s => {
    if (s.status !== "active") return s;
    if (s.bedId === bedId) return { ...s, roomId: undefined, bedId: undefined };
    return s;
  });

  state.students = state.students.map(s =>
    s.id === studentId ? { ...s, roomId, bedId } : s
  );

  const student = state.students.find(s => s.id === studentId);
  const room = state.rooms.find(r => r.id === roomId);
  const bed = state.beds.find(b => b.id === bedId);
  log(
    state,
    "BED_ASSIGNED",
    `Assigned ${student?.fullName ?? "student"} → ${room?.label ?? ""}/${bed?.label ?? ""}`
  );
  saveState(state);
}

export function unassignBed(studentId: string) {
  const state = loadState();
  const student = state.students.find(s => s.id === studentId);
  state.students = state.students.map(s =>
    s.id === studentId ? { ...s, roomId: undefined, bedId: undefined } : s
  );
  log(state, "BED_UNASSIGNED", `Unassigned bed from ${student?.fullName ?? "student"}`);
  saveState(state);
}

// ---------- Students ----------
export function addStudent(payload: Omit<Student, "id">) {
  const state = loadState();
  const student: Student = { ...payload, id: uid("stu") };
  state.students.unshift(student);
  log(state, "STUDENT_CREATED", `Student created: ${student.fullName}`);
  saveState(state);
  return student;
}

export function updateStudent(id: string, patch: Partial<Student>) {
  const state = loadState();
  state.students = state.students.map(s => (s.id === id ? { ...s, ...patch } : s));
  log(state, "STUDENT_UPDATED", `Student updated`);
  saveState(state);
}

// ---------- Due logic ----------
export function studentPaidInMonth(studentId: string, ym: string) {
  const state = loadState();
  return state.payments
    .filter(p => p.studentId === studentId && p.date.startsWith(ym))
    .reduce((a, p) => a + p.amount, 0);
}

export function studentDueInMonth(studentId: string, ym: string) {
  const state = loadState();
  const s = state.students.find(x => x.id === studentId);
  if (!s) return 0;
  const paid = studentPaidInMonth(studentId, ym);
  return Math.max(0, s.monthlyFee - paid);
}

// Vacating flow: only if due is cleared (for given month)
export function vacateStudentIfCleared(studentId: string, ym: string) {
  const state = loadState();
  const s = state.students.find(x => x.id === studentId);
  if (!s) return { ok: false, error: "Student not found" };

  const due = studentDueInMonth(studentId, ym);
  if (due > 0) return { ok: false, error: `Cannot vacate. Due remaining: ${due}` };

  state.students = state.students.map(x =>
    x.id === studentId
      ? { ...x, status: "vacated", roomId: undefined, bedId: undefined }
      : x
  );

  log(state, "STUDENT_VACATED", `Student vacated: ${s.fullName}`);
  saveState(state);
  return { ok: true };
}

// ---------- Expenses ----------
export function addExpense(payload: Omit<Expense, "id">) {
  const state = loadState();
  const expense: Expense = { ...payload, id: uid("exp") };
  state.expenses.unshift(expense);
  log(state, "EXPENSE_ADDED", `Expense: ${expense.category} Rs ${expense.amount}`);
  saveState(state);
  return expense;
}

export function updateExpense(id: string, patch: Partial<Expense>) {
  const state = loadState();
  state.expenses = state.expenses.map(e => (e.id === id ? { ...e, ...patch } : e));
  log(state, "EXPENSE_UPDATED", `Expense updated`);
  saveState(state);
}

export function deleteExpense(id: string) {
  const state = loadState();
  state.expenses = state.expenses.filter(e => e.id !== id);
  log(state, "EXPENSE_DELETED", `Expense deleted`);
  saveState(state);
}

// ---------- Payments ----------
export function addPayment(payload: Omit<Payment, "id">) {
  const state = loadState();
  const payment: Payment = { ...payload, id: uid("pay") };
  state.payments.unshift(payment);
  const s = state.students.find(x => x.id === payment.studentId);
  log(state, "PAYMENT_ADDED", `Payment: ${s?.fullName ?? "student"} Rs ${payment.amount}`);
  saveState(state);
  return payment;
}

// ---------- Backup / Restore ----------
export function exportBackup() {
  const state = loadState();
  log(state, "BACKUP_EXPORTED", "Backup exported");
  saveState(state);
  return state;
}

export function importBackup(next: HostelState) {
  // minimal safety checks
  if (!next || typeof next !== "object") throw new Error("Invalid backup format");
  // write
  lsSet(KEY, next);
  const state = loadState();
  log(state, "BACKUP_IMPORTED", "Backup imported");
  saveState(state);
}

// ---------- Demo seed ----------
export function seedDemoIfEmpty() {
  const state = loadState();
  const hasAny =
    state.students.length || state.expenses.length || state.payments.length || state.rooms.length || state.beds.length;
  if (hasAny) return;

  // Rooms + beds
  const r1: Room = { id: uid("room"), label: "101", floor: "1st" };
  const r2: Room = { id: uid("room"), label: "102", floor: "1st" };
  state.rooms = [r1, r2];

  const b1: Bed = { id: uid("bed"), roomId: r1.id, label: "B1" };
  const b2: Bed = { id: uid("bed"), roomId: r1.id, label: "B2" };
  const b3: Bed = { id: uid("bed"), roomId: r2.id, label: "B1" };
  state.beds = [b1, b2, b3];

  // Student
  const stu: Student = {
    id: uid("stu"),
    fullName: "Demo Student",
    phone: "98XXXXXXXX",
    monthlyFee: 9000,
    joinedAt: new Date().toISOString().slice(0, 10),
    status: "active",
    roomId: r1.id,
    bedId: b1.id,
  };

  state.students = [stu];

  // Payment + expense
  state.payments = [
    { id: uid("pay"), date: new Date().toISOString().slice(0, 10), studentId: stu.id, amount: 5000, note: "partial" },
  ];
  state.expenses = [
    { id: uid("exp"), date: new Date().toISOString().slice(0, 10), category: "Internet", amount: 1200, note: "WiFi" },
  ];

  log(state, "STUDENT_CREATED", "Demo data seeded");
  saveState(state);
}