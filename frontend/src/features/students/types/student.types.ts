export interface BedLite {
  id: string
  code?: string
  room?: string
  status?: string
}

export interface StudentDocument {
  id: string
  student: string
  doc_type: string
  file: string
  created_at: string
}

export interface Student {
  id: string
  full_name: string
  phone: string
  guardian_phone: string
  status: "ACTIVE" | "INACTIVE" | "LEFT"
  join_date?: string

  // IMPORTANT: assumes backend has Student.bed FK
  bed?: string | null

  // nested
  documents: StudentDocument[]
}
