import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import FormField from './FormField'
import type { VisitCreate } from '../api/types'

interface Props {
  title: string
  initial?: Partial<VisitCreate>
  submitLabel: string
  pending: boolean
  fieldErrors: Record<string, string>
  cancelTo: string
  onSubmit: (data: VisitCreate) => void
}
export default function VisitForm({ title, initial, submitLabel, pending, fieldErrors, cancelTo, onSubmit }: Props) {
  const [date, setDate] = useState(initial?.date ?? '')
  const [complaint, setComplaint] = useState(initial?.chief_complaint ?? '')
  const [diagnosis, setDiagnosis] = useState(initial?.diagnosis ?? '')
  const [notes, setNotes] = useState(initial?.notes ?? '')

  function submit(e: FormEvent) {
    e.preventDefault()
    onSubmit({ date, chief_complaint: complaint, diagnosis: diagnosis || null, notes: notes || null })
  }
  return (
    <form className="card form-card" onSubmit={submit}>
      <h2>{title}</h2>
      <FormField label="Date" name="date" required error={fieldErrors.date}>
        <input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </FormField>
      <FormField label="Chief Complaint" name="chief_complaint" required error={fieldErrors.chief_complaint}>
        <input id="chief_complaint" value={complaint} onChange={(e) => setComplaint(e.target.value)} />
      </FormField>
      <FormField label="Diagnosis" name="diagnosis" optional error={fieldErrors.diagnosis}>
        <input id="diagnosis" value={diagnosis ?? ''} onChange={(e) => setDiagnosis(e.target.value)} />
      </FormField>
      <FormField label="Notes" name="notes" optional error={fieldErrors.notes}>
        <textarea id="notes" value={notes ?? ''} onChange={(e) => setNotes(e.target.value)} />
      </FormField>
      <div className="modal-actions">
        <button type="submit" className="btn btn-primary" disabled={pending}>{submitLabel}</button>
        <Link to={cancelTo} className="btn btn-secondary">Cancel</Link>
      </div>
    </form>
  )
}
