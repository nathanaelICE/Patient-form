import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import FormField from './FormField'
import type { PatientCreate, Gender } from '../api/types'

type EmploymentStatus = 'employed' | 'unemployed' | 'retired' | 'student'

interface Props {
  title: string
  initial?: Partial<PatientCreate>
  submitLabel: string
  pending: boolean
  fieldErrors: Record<string, string>
  cancelTo: string
  onSubmit: (data: PatientCreate) => void
}
export default function PatientForm({ title, initial, submitLabel, pending, fieldErrors, cancelTo, onSubmit }: Props) {
  const [name, setName] = useState(initial?.name ?? '')
  const [dob, setDob] = useState(initial?.date_of_birth ?? '')
  const [gender, setGender] = useState<Gender>((initial?.gender as Gender) ?? 'male')
  const [phone, setPhone] = useState(initial?.phone ?? '')
  const [employmentStatus, setEmploymentStatus] = useState<EmploymentStatus | ''>((initial?.employment_status as EmploymentStatus) ?? '')
  const [income, setIncome] = useState(initial?.income ?? '')

  function submit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      name,
      date_of_birth: dob,
      gender,
      phone: phone || null,
      employment_status: employmentStatus || null,
      income: income === '' ? null : Number(income)
    })
  }
  return (
    <form className="card form-card" onSubmit={submit}>
      <h2>{title}</h2>
      <FormField label="Name" name="name" required error={fieldErrors.name}>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" />
      </FormField>
      <FormField label="Date of Birth" name="date_of_birth" required error={fieldErrors.date_of_birth}>
        <input id="date_of_birth" type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
      </FormField>
      <FormField label="Gender" name="gender" required error={fieldErrors.gender}>
        <select id="gender" value={gender} onChange={(e) => setGender(e.target.value as Gender)}>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
      </FormField>
      <FormField label="Phone" name="phone" optional error={fieldErrors.phone}>
        <input id="phone" value={phone ?? ''} onChange={(e) => setPhone(e.target.value)} placeholder="e.g. 08123456789" />
      </FormField>
      <FormField label="Employment Status" name="employment_status" optional error={fieldErrors.employment_status}>
        <select id="employment_status" value={employmentStatus} onChange={(e) => setEmploymentStatus(e.target.value as EmploymentStatus | '')}>
          <option value="">-- Select employment status --</option>
          <option value="employed">Employed</option>
          <option value="unemployed">Unemployed</option>
          <option value="retired">Retired</option>
          <option value="student">Student</option>
        </select>
      </FormField>
      <FormField label="Income" name="income" optional error={fieldErrors.income}>
        <input id="income" type="number" min="0" value={income} onChange={(e) => setIncome(e.target.value)} placeholder="e.g. 5000000" />
      </FormField>
      <div className="modal-actions">
        <button type="submit" className="btn btn-primary" disabled={pending}>{submitLabel}</button>
        <Link to={cancelTo} className="btn btn-secondary">Cancel</Link>
      </div>
    </form>
  )
}
