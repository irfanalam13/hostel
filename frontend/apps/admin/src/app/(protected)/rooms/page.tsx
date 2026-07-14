"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createBed,
  createBlock,
  createFloor,
  createRoom,
  getActiveAssignments,
  getAssignmentsByStudent,
  getBeds,
  getBlocks,
  getFloors,
  getRooms,
  transferBed,
} from "@/features/beds/api/bed.api";
import type { Bed, BedAssignment, Block, Floor, Room } from "@/features/beds/types/bed.types";
import { Topbar } from "@/components/shell/Topbar";
import { Button, Input, Modal, Select, Table, Textarea, useToast } from "@hostel/ui";

type Tab = "setup" | "occupancy";

function bedLabel(bed: Bed) {
  return bed.code || `${bed.room_detail?.room_no ?? ""}-${bed.bed_no}`;
}

export default function RoomsPage() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("setup");

  const [rooms, setRooms] = useState<Room[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [assignments, setAssignments] = useState<BedAssignment[]>([]);

  const [blockName, setBlockName] = useState("");
  const [floorName, setFloorName] = useState("");
  const [floorNumber, setFloorNumber] = useState("1");
  const [floorBlock, setFloorBlock] = useState("");
  const [roomNo, setRoomNo] = useState("");
  const [roomBlock, setRoomBlock] = useState("");
  const [roomFloorRef, setRoomFloorRef] = useState("");
  const [floor, setFloor] = useState("");
  const [capacity, setCapacity] = useState("1");
  const [rent, setRent] = useState("0");
  const [roomType, setRoomType] = useState("Standard");
  const [bedRoom, setBedRoom] = useState("");
  const [bedNo, setBedNo] = useState("");
  const [error, setError] = useState("");

  // Transfer modal
  const [transferFor, setTransferFor] = useState<BedAssignment | null>(null);
  const [targetBed, setTargetBed] = useState("");
  const [transferNote, setTransferNote] = useState("");
  const [transferBusy, setTransferBusy] = useState(false);

  // History modal
  const [historyFor, setHistoryFor] = useState<BedAssignment | null>(null);
  const [history, setHistory] = useState<BedAssignment[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  async function refresh() {
    setError("");
    try {
      const [blockData, floorData, roomData, bedData, assignData] = await Promise.all([
        getBlocks(),
        getFloors(),
        getRooms(),
        getBeds(),
        getActiveAssignments(),
      ]);
      setBlocks(blockData);
      setFloors(floorData);
      setRooms(roomData);
      setBeds(bedData);
      setAssignments(assignData);
    } catch (err: any) {
      setError(err?.message || "Failed to load rooms.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function saveRoom(e: React.FormEvent) {
    e.preventDefault();
    await createRoom({
      room_no: roomNo,
      block: roomBlock || null,
      floor_ref: roomFloorRef || null,
      floor,
      capacity: Number(capacity || 1),
      rent,
      room_type: roomType,
      gender_type: "ANY",
      status: "ACTIVE",
    });
    setRoomNo("");
    setRoomBlock("");
    setRoomFloorRef("");
    setFloor("");
    setCapacity("1");
    setRent("0");
    await refresh();
  }

  async function saveBlock(e: React.FormEvent) {
    e.preventDefault();
    await createBlock({ name: blockName });
    setBlockName("");
    await refresh();
  }

  async function saveFloor(e: React.FormEvent) {
    e.preventDefault();
    await createFloor({ block: floorBlock, name: floorName, number: Number(floorNumber || 0) });
    setFloorName("");
    setFloorNumber("1");
    await refresh();
  }

  async function saveBed(e: React.FormEvent) {
    e.preventDefault();
    await createBed({ room: bedRoom, bed_no: bedNo, status: "AVAILABLE" });
    setBedNo("");
    await refresh();
  }

  // ---- Occupancy derivations ----
  const stats = useMemo(() => {
    const total = beds.length;
    const occupied = beds.filter((b) => b.status === "OCCUPIED").length;
    const available = beds.filter((b) => b.status === "AVAILABLE").length;
    const maintenance = beds.filter((b) => b.status === "MAINTENANCE").length;
    return { total, occupied, available, maintenance };
  }, [beds]);

  const perRoom = useMemo(() => {
    return rooms.map((room) => {
      const roomBeds = beds.filter((b) => b.room === room.id);
      return {
        room,
        total: roomBeds.length,
        occupied: roomBeds.filter((b) => b.status === "OCCUPIED").length,
        available: roomBeds.filter((b) => b.status === "AVAILABLE").length,
      };
    });
  }, [rooms, beds]);

  const availableBeds = useMemo(() => beds.filter((b) => b.status === "AVAILABLE"), [beds]);

  function openTransfer(a: BedAssignment) {
    setTransferFor(a);
    setTargetBed("");
    setTransferNote("");
  }

  async function confirmTransfer() {
    if (!transferFor || !targetBed) return;
    setTransferBusy(true);
    try {
      await transferBed({ student: transferFor.student, bed: targetBed, note: transferNote });
      toast.success("Bed transfer complete.");
      setTransferFor(null);
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Transfer failed.");
    } finally {
      setTransferBusy(false);
    }
  }

  async function openHistory(a: BedAssignment) {
    setHistoryFor(a);
    setHistory([]);
    setHistoryLoading(true);
    try {
      setHistory(await getAssignmentsByStudent(a.student));
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }

  return (
    <div>
      <Topbar title="Rooms" />
      {error ? <div className="mb-3 text-sm text-red-600">{error}</div> : null}

      <div className="mb-4 flex gap-2">
        <Button variant={tab === "setup" ? "primary" : "ghost"} onClick={() => setTab("setup")}>
          Setup
        </Button>
        <Button variant={tab === "occupancy" ? "primary" : "ghost"} onClick={() => setTab("occupancy")}>
          Occupancy
        </Button>
      </div>

      {tab === "setup" ? (
        <>
          <div className="grid gap-4 md:grid-cols-4 mb-4">
            <form onSubmit={saveBlock} className="rounded-2xl border bg-white p-4 space-y-3">
              <div className="font-semibold">Add Block</div>
              <Input label="Block name" value={blockName} onChange={(e) => setBlockName(e.target.value)} required />
              <Button type="submit">Save Block</Button>
            </form>

            <form onSubmit={saveFloor} className="rounded-2xl border bg-white p-4 space-y-3">
              <div className="font-semibold">Add Floor</div>
              <select className="w-full px-3 py-2 rounded-lg border border-gray-200" value={floorBlock} onChange={(e) => setFloorBlock(e.target.value)} required>
                <option value="">Block</option>
                {blocks.map((block) => (
                  <option key={block.id} value={block.id}>{block.name}</option>
                ))}
              </select>
              <Input label="Floor name" value={floorName} onChange={(e) => setFloorName(e.target.value)} required />
              <Input label="Floor no" value={floorNumber} onChange={(e) => setFloorNumber(e.target.value)} />
              <Button type="submit">Save Floor</Button>
            </form>

            <form onSubmit={saveRoom} className="rounded-2xl border bg-white p-4 space-y-3">
              <div className="font-semibold">Add Room</div>
              <select className="w-full px-3 py-2 rounded-lg border border-gray-200" value={roomBlock} onChange={(e) => setRoomBlock(e.target.value)}>
                <option value="">Block</option>
                {blocks.map((block) => (
                  <option key={block.id} value={block.id}>{block.name}</option>
                ))}
              </select>
              <select className="w-full px-3 py-2 rounded-lg border border-gray-200" value={roomFloorRef} onChange={(e) => setRoomFloorRef(e.target.value)}>
                <option value="">Floor</option>
                {floors.filter((item) => !roomBlock || item.block === roomBlock).map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
              <Input label="Room No" value={roomNo} onChange={(e) => setRoomNo(e.target.value)} required />
              <Input label="Floor label" value={floor} onChange={(e) => setFloor(e.target.value)} />
              <Input label="Type" value={roomType} onChange={(e) => setRoomType(e.target.value)} />
              <Input label="Capacity" value={capacity} onChange={(e) => setCapacity(e.target.value)} />
              <Input label="Rent (Rs.)" value={rent} onChange={(e) => setRent(e.target.value)} />
              <Button type="submit">Save Room</Button>
            </form>

            <form onSubmit={saveBed} className="rounded-2xl border bg-white p-4 space-y-3">
              <div className="font-semibold">Add Bed</div>
              <select
                className="w-full px-3 py-2 rounded-lg border border-gray-200"
                value={bedRoom}
                onChange={(e) => setBedRoom(e.target.value)}
                required
              >
                <option value="">Select room</option>
                {rooms.map((room) => (
                  <option key={room.id} value={room.id}>
                    {room.room_no}
                  </option>
                ))}
              </select>
              <Input label="Bed No" value={bedNo} onChange={(e) => setBedNo(e.target.value)} required />
              <Button type="submit">Save Bed</Button>
            </form>
          </div>

          <Table>
            <thead>
              <tr className="text-left border-b">
                <th className="p-3">Room</th>
                <th className="p-3">Block</th>
                <th className="p-3">Floor</th>
                <th className="p-3">Rent</th>
                <th className="p-3">Beds</th>
              </tr>
            </thead>
            <tbody>
              {rooms.map((room) => (
                <tr key={room.id} className="border-b">
                  <td className="p-3 font-medium">{room.room_no}</td>
                  <td className="p-3">{room.block_detail?.name || "-"}</td>
                  <td className="p-3">{room.floor_detail?.name || room.floor || "-"}</td>
                  <td className="p-3">{room.rent || "0"}</td>
                  <td className="p-3">
                    {beds
                      .filter((bed) => bed.room === room.id)
                      .map((bed) => `${bed.bed_no} (${bed.status})`)
                      .join(", ") || "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-4 mb-4">
            <StatCard label="Total beds" value={stats.total} />
            <StatCard label="Occupied" value={stats.occupied} tone="text-emerald-600" />
            <StatCard label="Available" value={stats.available} tone="text-blue-600" />
            <StatCard label="Maintenance" value={stats.maintenance} tone="text-amber-600" />
          </div>

          <div className="mb-2 text-sm font-semibold text-[var(--foreground-secondary)]">Occupancy by room</div>
          <Table>
            <thead>
              <tr className="text-left border-b">
                <th className="p-3">Room</th>
                <th className="p-3">Beds</th>
                <th className="p-3">Occupied</th>
                <th className="p-3">Available</th>
              </tr>
            </thead>
            <tbody>
              {perRoom.map(({ room, total, occupied, available }) => (
                <tr key={room.id} className="border-b">
                  <td className="p-3 font-medium">{room.room_no}</td>
                  <td className="p-3">{total}</td>
                  <td className="p-3">{occupied}</td>
                  <td className="p-3">{available}</td>
                </tr>
              ))}
            </tbody>
          </Table>

          <div className="mb-2 mt-6 text-sm font-semibold text-[var(--foreground-secondary)]">
            Current allocations
          </div>
          <p className="mb-2 text-xs text-[var(--muted)]">
            Initial beds are assigned when an admission is approved. Use Transfer to move a resident to a
            different bed — the full history is preserved.
          </p>
          <Table>
            <thead>
              <tr className="text-left border-b">
                <th className="p-3">Student</th>
                <th className="p-3">Current bed</th>
                <th className="p-3">Since</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {assignments.length === 0 ? (
                <tr>
                  <td className="p-3 text-sm text-[var(--muted)]" colSpan={4}>
                    No active allocations yet.
                  </td>
                </tr>
              ) : (
                assignments.map((a) => (
                  <tr key={a.id} className="border-b">
                    <td className="p-3 font-medium">{a.student_name || a.student}</td>
                    <td className="p-3">{a.bed_code || a.bed}</td>
                    <td className="p-3">{a.start_date}</td>
                    <td className="p-3">
                      <div className="flex gap-2">
                        <Button variant="ghost" onClick={() => openTransfer(a)}>
                          Transfer
                        </Button>
                        <Button variant="ghost" onClick={() => openHistory(a)}>
                          History
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </Table>
        </>
      )}

      <Modal
        open={!!transferFor}
        title="Transfer bed"
        onClose={() => (transferBusy ? undefined : setTransferFor(null))}
      >
        {transferFor ? (
          <div className="space-y-3">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-3 text-sm">
              <div>
                <span className="text-[var(--muted)]">Student: </span>
                <span className="font-medium">{transferFor.student_name || transferFor.student}</span>
              </div>
              <div>
                <span className="text-[var(--muted)]">Current bed: </span>
                <span className="font-medium">{transferFor.bed_code || transferFor.bed}</span>
              </div>
            </div>
            <Select
              label="Move to bed"
              placeholder="Select an available bed"
              value={targetBed}
              onChange={(e) => setTargetBed(e.target.value)}
              options={availableBeds.map((b) => ({ value: b.id, label: bedLabel(b) }))}
            />
            {availableBeds.length === 0 ? (
              <div className="text-xs text-amber-600">No available beds. Add or free a bed first.</div>
            ) : null}
            <Textarea
              label="Reason / note (optional)"
              value={transferNote}
              onChange={(e) => setTransferNote(e.target.value)}
              placeholder="e.g. Roommate conflict, upgrade request"
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setTransferFor(null)} disabled={transferBusy}>
                Cancel
              </Button>
              <Button onClick={confirmTransfer} disabled={transferBusy || !targetBed}>
                {transferBusy ? "Transferring…" : "Confirm transfer"}
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal open={!!historyFor} title="Assignment history" onClose={() => setHistoryFor(null)}>
        {historyLoading ? (
          <div className="text-sm text-[var(--muted)]">Loading…</div>
        ) : history.length === 0 ? (
          <div className="text-sm text-[var(--muted)]">No history found.</div>
        ) : (
          <div className="space-y-2">
            {history.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between rounded-xl border border-[var(--border)] p-3 text-sm"
              >
                <div>
                  <div className="font-medium">{h.bed_code || h.bed}</div>
                  <div className="text-xs text-[var(--muted)]">
                    {h.start_date} → {h.end_date || "present"}
                    {h.reason ? ` · ${h.reason}` : ""}
                    {h.note ? ` · ${h.note}` : ""}
                  </div>
                </div>
                {h.is_active ? (
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                    Active
                  </span>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}

function StatCard({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-2xl border bg-white p-4">
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className={`text-2xl font-semibold ${tone || ""}`}>{value}</div>
    </div>
  );
}
