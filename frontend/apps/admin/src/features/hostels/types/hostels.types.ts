export type Hostel = {
  id: string;
  name: string;
  code: string;
  address: string;
  phone: string;
  is_active: boolean;
  created_at: string;
};

export type Room = {
  id: string;
  hostel: string;
  number: string;
  floor?: string;
  notes?: string;
  created_at: string;
};
