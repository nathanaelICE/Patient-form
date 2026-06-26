import { FormEvent, useState } from 'react'
import FormField from './FormField'
import type { VisitCreate } from '../api/types'

interface Props {
  initial?: Partial<VisitCreate>
  submitLabel: string
  pending: boolean
  fieldErrors: Record<string, string>
  onSubmit: (data: VisitCreate) => void
}
export default function VisitForm({ initial, submitLabel, pending, fieldErrors, onSubmit }: Props) {
  const [date, setDate] = useState(initial?.date ?? '')
  const [complaint, setComplaint] = useState(initial?.chief_complaint ?? '')
  const [diagnosis, setDiagnosis] = useState(initial?.diagnosis ?? '')
  const [notes, setNotes] = useState(initial?.notes ?? '')

  function submit(e: FormEvent) {
    e.preventDefault()
    onSubmit({ date, chief_complaint: complaint, diagnosis: diagnosis || null, notes: notes || null })
  }
  return (
    <form className="card" onSubmit={submit}>
      <FormField label="Date" name="date" error={fieldErrors.date}>
        <input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </FormField>
      <FormField label="Chief complaint" name="chief_complaint" error={fieldErrors.chief_complaint}>
        <input id="chief_complaint" value={complaint} onChange={(e) => setComplaint(e.target.value)} />
      </FormField>
      <FormField label="Diagnosis" name="diagnosis" error={fieldErrors.diagnosis}>
        <input id="diagnosis" value={diagnosis ?? ''} onChange={(e) => setDiagnosis(e.target.value)} />
      </FormField>
      <FormField label="Notes" name="notes" error={fieldErrors.notes}>
        <textarea id="notes" value={notes ?? ''} onChange={(e) => setNotes(e.target.value)} />
      </FormField>
      <button type="submit" disabled={pending}>{submitLabel}</button>
    </form>
  )
}
