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
  lowConfidence?: Record<string, number>
}

const LOW_CONF = 0.6

export default function PatientForm({
  title, initial, submitLabel, pending, fieldErrors, cancelTo, onSubmit, lowConfidence,
}: Props) {
  const [name, setName] = useState(initial?.name ?? '')
  const [dob, setDob] = useState(initial?.date_of_birth ?? '')
  const [gender, setGender] = useState<Gender>((initial?.gender as Gender) ?? 'male')
  const [phone, setPhone] = useState(initial?.phone ?? '')
  const [nationalId, setNationalId] = useState(initial?.national_id ?? '')
  const [placeOfBirth, setPlaceOfBirth] = useState(initial?.place_of_birth ?? '')
  const [maritalStatus, setMaritalStatus] = useState(initial?.marital_status ?? '')
  const [occupation, setOccupation] = useState(initial?.occupation ?? '')
  const [religion, setReligion] = useState(initial?.religion ?? '')
  const [nationality, setNationality] = useState(initial?.nationality ?? '')
  const [bloodType, setBloodType] = useState(initial?.blood_type ?? '')
  const [allergies, setAllergies] = useState(initial?.allergies ?? '')
  const [knownConditions, setKnownConditions] = useState(initial?.known_conditions ?? '')
  const [employmentStatus, setEmploymentStatus] = useState<EmploymentStatus | ''>((initial?.employment_status as EmploymentStatus) ?? '')
  const [income, setIncome] = useState(initial?.income ?? '')

  function lowConf(field: string): boolean {
    const c = lowConfidence?.[field]
    return c !== undefined && c < LOW_CONF
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      name,
      date_of_birth: dob,
      gender,
      phone: phone || null,
      national_id: nationalId || null,
      place_of_birth: placeOfBirth || null,
      marital_status: maritalStatus || null,
      occupation: occupation || null,
      religion: religion || null,
      nationality: nationality || null,
      blood_type: bloodType || null,
      allergies: allergies || null,
      known_conditions: knownConditions || null,
      employment_status: employmentStatus || null,
      income: income === '' ? null : Number(income),
    })
  }

  return (
    <form className="card form-card" onSubmit={submit}>
      <h2>{title}</h2>
      <FormField label="Name" name="name" required error={fieldErrors.name} className={lowConf('name') ? 'field-low-confidence' : undefined}>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" />
      </FormField>
      <FormField label="Date of Birth" name="date_of_birth" required error={fieldErrors.date_of_birth} className={lowConf('date_of_birth') ? 'field-low-confidence' : undefined}>
        <input id="date_of_birth" type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
      </FormField>
      <FormField label="Gender" name="gender" required error={fieldErrors.gender} className={lowConf('gender') ? 'field-low-confidence' : undefined}>
        <select id="gender" value={gender} onChange={(e) => setGender(e.target.value as Gender)}>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
      </FormField>
      <FormField label="Phone" name="phone" optional error={fieldErrors.phone} className={lowConf('phone') ? 'field-low-confidence' : undefined}>
        <input id="phone" value={phone ?? ''} onChange={(e) => setPhone(e.target.value)} placeholder="e.g. 08123456789" />
      </FormField>
      <FormField label="National ID (NIK)" name="national_id" optional error={fieldErrors.national_id} className={lowConf('national_id') ? 'field-low-confidence' : undefined}>
        <input id="national_id" value={nationalId ?? ''} onChange={(e) => setNationalId(e.target.value)} placeholder="16-digit NIK" />
      </FormField>
      <FormField label="Place of Birth" name="place_of_birth" optional error={fieldErrors.place_of_birth} className={lowConf('place_of_birth') ? 'field-low-confidence' : undefined}>
        <input id="place_of_birth" value={placeOfBirth ?? ''} onChange={(e) => setPlaceOfBirth(e.target.value)} />
      </FormField>
      <FormField label="Marital Status" name="marital_status" optional error={fieldErrors.marital_status} className={lowConf('marital_status') ? 'field-low-confidence' : undefined}>
        <select id="marital_status" value={maritalStatus ?? ''} onChange={(e) => setMaritalStatus(e.target.value)}>
          <option value="">—</option>
          <option value="single">Single</option>
          <option value="married">Married</option>
          <option value="divorced">Divorced</option>
          <option value="widowed">Widowed</option>
        </select>
      </FormField>
      <FormField label="Occupation" name="occupation" optional error={fieldErrors.occupation} className={lowConf('occupation') ? 'field-low-confidence' : undefined}>
        <input id="occupation" value={occupation ?? ''} onChange={(e) => setOccupation(e.target.value)} />
      </FormField>
      <FormField label="Religion" name="religion" optional error={fieldErrors.religion} className={lowConf('religion') ? 'field-low-confidence' : undefined}>
        <input id="religion" value={religion ?? ''} onChange={(e) => setReligion(e.target.value)} />
      </FormField>
      <FormField label="Nationality" name="nationality" optional error={fieldErrors.nationality} className={lowConf('nationality') ? 'field-low-confidence' : undefined}>
        <input id="nationality" value={nationality ?? ''} onChange={(e) => setNationality(e.target.value)} placeholder="e.g. Indonesian" />
      </FormField>
      <FormField label="Blood Type" name="blood_type" optional error={fieldErrors.blood_type} className={lowConf('blood_type') ? 'field-low-confidence' : undefined}>
        <select id="blood_type" value={bloodType ?? ''} onChange={(e) => setBloodType(e.target.value)}>
          <option value="">—</option>
          {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'A', 'B', 'AB', 'O'].map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
      </FormField>
      <FormField label="Allergies" name="allergies" optional error={fieldErrors.allergies} className={lowConf('allergies') ? 'field-low-confidence' : undefined}>
        <input id="allergies" value={allergies ?? ''} onChange={(e) => setAllergies(e.target.value)} />
      </FormField>
      <FormField label="Known Conditions" name="known_conditions" optional error={fieldErrors.known_conditions} className={lowConf('known_conditions') ? 'field-low-confidence' : undefined}>
        <input id="known_conditions" value={knownConditions ?? ''} onChange={(e) => setKnownConditions(e.target.value)} />
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
