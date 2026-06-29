"use client";

import { useMemo, useState } from "react";
import { Topbar } from "@/shared/ui/Topbar";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Modal } from "@/shared/ui/Modal";
import { Table } from "@/shared/ui/Table";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import { loadState, addRoom, addBed, assignBed, unassignBed } from "@/features/hostels/store";
import { occupancy } from "@/shared/lib/finance";

export default function BedsPage() {
  const toast = useToast();
  const [tick, setTick] = useState(0);

  const [roomOpen, setRoomOpen] = useState(false);
  const [bedOpen, setBedOpen] = useState(false);

  const [roomLabel, setRoomLabel] = useState("");
  const [floor, setFloor] = useState("");

  const [bedRoomId, setBedRoomId] = useState("");
  const [bedLabel, setBedLabel] = useState("");

  // assign modal
  const [assignOpen, setAssignOpen] = useState(false);
  const [assignStudentId, setAssignStudentId] = useState("");
  const [assignRoomId, setAssignRoomId] = useState("");
  const [assignBedId, setAssignBedId] = useState("");

  const state = useMemo(() => loadState(), [tick]);
  const rooms = state.rooms;
  const beds = state.beds;
  const students = state.students.filter(s => s.status === "active");
  const occ = occupancy(state.students, rooms, beds);

  function refresh() { setTick(t => t + 1); }

  function createRoom() {
    if (!roomLabel.trim()) return toast.warning("Room label is required.");
    const r = addRoom({ label: roomLabel.trim(), floor: floor.trim() || undefined });
    setRoomLabel(""); setFloor("");
    setRoomOpen(false);
    if (!bedRoomId) setBedRoomId(r.id);
    toast.success("Room created.");
    refresh();
  }

  function createBed() {
    if (!bedRoomId) return toast.warning("Please select a room.");
    if (!bedLabel.trim()) return toast.warning("Bed label is required.");
    addBed({ roomId: bedRoomId, label: bedLabel.trim() });
    setBedLabel("");
    setBedOpen(false);
    toast.success("Bed created.");
    refresh();
  }

  function openAssign() {
    if (!students.length) return toast.warning("No active students to assign.");
    if (!rooms.length || !beds.length) return toast.warning("Create rooms and beds first.");
    setAssignStudentId(students[0].id);
    setAssignRoomId(rooms[0].id);
    const roomBeds = beds.filter(b => b.roomId === rooms[0].id);
    setAssignBedId(roomBeds[0]?.id ?? "");
    setAssignOpen(true);
  }

  function doAssign() {
    if (!assignStudentId || !assignRoomId || !assignBedId) {
      return toast.warning("Please select a student, room and bed.");
    }
    assignBed(assignStudentId, assignRoomId, assignBedId);
    setAssignOpen(false);
    toast.success("Bed assigned.");
    refresh();
  }

  return (
    <div>
      <Topbar title="Beds & Rooms" />

      <div className="flex flex-wrap gap-2 justify-between items-center mb-3">
        <div className="text-sm text-gray-600">
          Total beds: <b>{occ.totalBeds}</b> | Occupied: <b>{occ.occupied}</b> | Available: <b>{occ.available}</b>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => setRoomOpen(true)}>Add Room</Button>
          <Button variant="ghost" onClick={() => setBedOpen(true)}>Add Bed</Button>
          <Button onClick={openAssign}>Assign Bed</Button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Table>
          <thead>
            <tr className="text-left border-b border-gray-200">
              <th className="p-3">Room</th>
              <th className="p-3">Beds</th>
              <th className="p-3">Occupied</th>
              <th className="p-3">Available</th>
            </tr>
          </thead>
          <tbody>
            {occ.byRoom.map(r => (
              <tr key={r.room} className="border-b border-gray-100">
                <td className="p-3 font-medium">{r.room}</td>
                <td className="p-3">{r.totalBeds}</td>
                <td className="p-3">{r.occupied}</td>
                <td className="p-3">{r.available}</td>
              </tr>
            ))}
            {occ.byRoom.length === 0 ? (
              <tr><td className="p-4 text-gray-500" colSpan={4}>No rooms yet.</td></tr>
            ) : null}
          </tbody>
        </Table>

        <Table>
          <thead>
            <tr className="text-left border-b border-gray-200">
              <th className="p-3">Student</th>
              <th className="p-3">Assigned</th>
              <th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {students.map(s => {
              const room = rooms.find(r => r.id === s.roomId);
              const bed = beds.find(b => b.id === s.bedId);
              const assigned = room && bed ? `${room.label}/${bed.label}` : "-";
              return (
                <tr key={s.id} className="border-b border-gray-100">
                  <td className="p-3">{s.fullName}</td>
                  <td className="p-3">{assigned}</td>
                  <td className="p-3">
                    <Button variant="danger" onClick={() => { unassignBed(s.id); refresh(); }}>
                      Unassign
                    </Button>
                  </td>
                </tr>
              );
            })}
            {students.length === 0 ? (
              <tr><td className="p-4 text-gray-500" colSpan={3}>No active students.</td></tr>
            ) : null}
          </tbody>
        </Table>
      </div>

      {/* Add Room */}
      <Modal open={roomOpen} title="Add Room" onClose={() => setRoomOpen(false)}>
        <div className="grid gap-3">
          <Input label="Room Label (e.g. 101)" value={roomLabel} onChange={(e) => setRoomLabel(e.target.value)} />
          <Input label="Floor (optional)" value={floor} onChange={(e) => setFloor(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setRoomOpen(false)}>Cancel</Button>
            <Button onClick={createRoom}>Create</Button>
          </div>
        </div>
      </Modal>

      {/* Add Bed */}
      <Modal open={bedOpen} title="Add Bed" onClose={() => setBedOpen(false)}>
        <div className="grid gap-3">
          <label className="block">
            <div className="text-sm mb-1 text-gray-700">Room</div>
            <select
              className="w-full px-3 py-2 rounded-lg border border-gray-200"
              value={bedRoomId}
              onChange={(e) => setBedRoomId(e.target.value)}
            >
              <option value="">Select room</option>
              {rooms.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>
          </label>
          <Input label="Bed Label (e.g. B1)" value={bedLabel} onChange={(e) => setBedLabel(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setBedOpen(false)}>Cancel</Button>
            <Button onClick={createBed}>Create</Button>
          </div>
        </div>
      </Modal>

      {/* Assign */}
      <Modal open={assignOpen} title="Assign Bed to Student" onClose={() => setAssignOpen(false)}>
        <div className="grid gap-3">
          <label className="block">
            <div className="text-sm mb-1 text-gray-700">Student</div>
            <select
              className="w-full px-3 py-2 rounded-lg border border-gray-200"
              value={assignStudentId}
              onChange={(e) => setAssignStudentId(e.target.value)}
            >
              {students.map(s => <option key={s.id} value={s.id}>{s.fullName}</option>)}
            </select>
          </label>

          <label className="block">
            <div className="text-sm mb-1 text-gray-700">Room</div>
            <select
              className="w-full px-3 py-2 rounded-lg border border-gray-200"
              value={assignRoomId}
              onChange={(e) => {
                const rid = e.target.value;
                setAssignRoomId(rid);
                const roomBeds = beds.filter(b => b.roomId === rid);
                setAssignBedId(roomBeds[0]?.id ?? "");
              }}
            >
              {rooms.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>
          </label>

          <label className="block">
            <div className="text-sm mb-1 text-gray-700">Bed</div>
            <select
              className="w-full px-3 py-2 rounded-lg border border-gray-200"
              value={assignBedId}
              onChange={(e) => setAssignBedId(e.target.value)}
            >
              {beds.filter(b => b.roomId === assignRoomId).map(b => (
                <option key={b.id} value={b.id}>{b.label}</option>
              ))}
            </select>
          </label>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setAssignOpen(false)}>Cancel</Button>
            <Button onClick={doAssign}>Assign</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}