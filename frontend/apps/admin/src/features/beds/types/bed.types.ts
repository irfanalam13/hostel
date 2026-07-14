export interface Block {
  id: string;
  name: string;
  code?: string;
  description?: string;
}

export interface Floor {
  id: string;
  block: string;
  block_detail?: Block;
  name: string;
  number?: number;
}

export interface Room {
  id: string;
  hostel?: string;
  block?: string | null;
  block_detail?: Block;
  floor_ref?: string | null;
  floor_detail?: Floor;
  room_no: string;
  floor?: string;
  room_type?: string;
  capacity?: number;
  rent?: string;
  amenities?: string[];
  status?: "ACTIVE" | "MAINTENANCE" | "INACTIVE" | string;
  gender_type?: "MALE" | "FEMALE" | "ANY" | string;
  created_at?: string;
}

export interface Bed {
  id: string;
  hostel?: string;
  room: string;
  room_detail?: Room;
  code?: string;
  bed_no: string;
  status: "AVAILABLE" | "OCCUPIED" | "MAINTENANCE" | string;
  created_at?: string;
}

export interface BedAssignment {
  id: string;
  hostel?: string;
  bed: string;
  student: string;
  start_date: string;
  end_date?: string | null;
  is_active: boolean;
  reason?: "INITIAL" | "TRANSFER" | string;
  note?: string;
  created_by?: string | null;
  previous_assignment?: string | null;
  // Read-only display fields from the API
  student_name?: string;
  bed_code?: string;
  room_no?: string;
  created_by_name?: string;
  created_at?: string;
}
