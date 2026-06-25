"use client"

import StudentForm from "@/features/students/components/StudentForm"

export default function NewStudentPage() {
  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">Add Student</h1>
      <StudentForm />
    </div>
  )
}