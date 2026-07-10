"use client";

import { useEffect, useState } from "react";
import { createBed, createBlock, createFloor, createRoom, getBeds, getBlocks, getFloors, getRooms } from "@/features/beds/api/bed.api";
import type { Bed, Block, Floor, Room } from "@/features/beds/types/bed.types";
import { Topbar } from "@/components/shell/Topbar";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";

export default function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
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

  async function refresh() {
    setError("");
    try {
      const [blockData, floorData, roomData, bedData] = await Promise.all([
        getBlocks(),
        getFloors(),
        getRooms(),
        getBeds(),
      ]);
      setBlocks(blockData);
      setFloors(floorData);
      setRooms(roomData);
      setBeds(bedData);
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

  return (
    <div>
      <Topbar title="Rooms" />
      {error ? <div className="mb-3 text-sm text-red-600">{error}</div> : null}

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
    </div>
  );
}
