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

export type Gender = "MALE" | "FEMALE" | "OTHER"

export interface Student {
  id: string
  full_name: string
  name_nepali?: string
  phone: string
  address?: string
  guardian_name?: string
  guardian_phone: string
  status: "ACTIVE" | "LEFT"
  join_date?: string

  // Extended profile (mirrors backend Student model — populated on admission approval)
  date_of_birth?: string | null
  gender?: Gender
  photo?: string | null
  citizenship_number?: string
  father_name?: string
  mother_name?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
  emergency_contact_relation?: string

  // IMPORTANT: assumes backend has Student.bed FK
  bed?: string | null

  // nested
  documents: StudentDocument[]
}
