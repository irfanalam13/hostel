"use client"

import { useState } from "react"
import { uploadDocument } from "../api/document.api"
import { Student } from "../types/student.types"
import { useToast } from "@/shared/ui/toast/ToastProvider"
import { Spinner } from "@/shared/ui/Spinner"

export default function StudentDocuments({ student }: { student: Student }) {
  const toast = useToast()
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append("student", student.id.toString())
    formData.append("doc_type", "ID_CARD")
    formData.append("file", file)

    setUploading(true)
    try {
      await uploadDocument(formData)
      toast.success("Document uploaded.")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed.")
    } finally {
      setUploading(false)
      // Reset the input so the same file can be re-selected if needed.
      e.target.value = ""
    }
  }

  return (
    <div className="mt-6">
      <h2 className="font-semibold">Documents</h2>

      <ul className="mb-4">
        {student.documents.map((doc) => (
          <li key={doc.id}>
            {doc.doc_type} -{" "}
            <a href={doc.file} target="_blank" className="text-blue-600">
              View
            </a>
          </li>
        ))}
      </ul>

      <div className="flex items-center gap-2">
        <input type="file" onChange={handleUpload} disabled={uploading} />
        {uploading ? <Spinner size="sm" /> : null}
      </div>
    </div>
  )
}
