import { FormEvent, useState } from 'react'
import FormField from './FormField'
import type { PatientCreate, Gender } from '../api/types'

interface Props {
  initial?: Partial<PatientCreate>
  submitLabel: string
  pending: boolean
  fieldErrors: Record<string, string>
  onSubmit: (data: PatientCreate) => void
}
export default function PatientForm({ initial, submitLabel, pending, fieldErrors, onSubmit }: Props) {
  const [name, setName] = useState(initial?.name ?? '')
  const [dob, setDob] = useState(initial?.date_of_birth ?? '')
  const [gender, setGender] = useState<Gender>((initial?.gender as Gender) ?? 'male')
  const [phone, setPhone] = useState(initial?.phone ?? '')

  function submit(e: FormEvent) {
    e.preventDefault()
    onSubmit({ name, date_of_birth: dob, gender, phone: phone || null })
  }
  return (
    <form className="card" onSubmit={submit}>
      <FormField label="Name" name="name" error={fieldErrors.name}>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} />
      </FormField>
      <FormField label="Date of birth" name="date_of_birth" error={fieldErrors.date_of_birth}>
        <input id="date_of_birth" type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
      </FormField>
      <FormField label="Gender" name="gender" error={fieldErrors.gender}>
        <select id="gender" value={gender} onChange={(e) => setGender(e.target.value as Gender)}>
          <option value="male">male</option>
          <option value="female">female</option>
          <option value="other">other</option>
        </select>
      </FormField>
      <FormField label="Phone" name="phone" error={fieldErrors.phone}>
        <input id="phone" value={phone ?? ''} onChange={(e) => setPhone(e.target.value)} />
      </FormField>
      <button type="submit" disabled={pending}>{submitLabel}</button>
    </form>
  )
}
