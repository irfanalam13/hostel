export type Notice = {
  id: string;
  title: string;
  body: string;
  target_type: "ALL" | "BLOCK" | "FLOOR" | "ROOM" | "ROLE";
  target_value?: string;
  is_pinned: boolean;
  published_at?: string;
  expires_at?: string | null;
  created_by_name?: string;
};
