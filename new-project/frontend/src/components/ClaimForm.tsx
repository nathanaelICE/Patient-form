import { useState, FormEvent } from 'react'
import FormField from './FormField'
import type { ClaimCreate, ClaimStatus, ClaimType, ClaimMethod } from '../api/types'

interface Props {
  onSubmit: (body: ClaimCreate) => void
  pending: boolean
  fieldErrors?: Record<string, string>
}

const TYPES: ClaimType[] = ['inpatient', 'outpatient', 'emergency', 'routine']
const METHODS: ClaimMethod[] = ['online', 'paper', 'phone']
const STATUSES: ClaimStatus[] = ['pending', 'approved', 'denied']

export default function ClaimForm({ onSubmit, pending, fieldErrors = {} }: Props) {
  const [claimDate, setClaimDate] = useState('')
  const [amount, setAmount] = useState('')
  const [status, setStatus] = useState<ClaimStatus>('pending')
  const [type, setType] = useState<ClaimType>('outpatient')
  const [method, setMethod] = useState<ClaimMethod>('online')
  const [diagnosisCode, setDiagnosisCode] = useState('')
  const [procedureCode, setProcedureCode] = useState('')
  const [providerId, setProviderId] = useState('')
  const [providerSpecialty, setProviderSpecialty] = useState('')
  const [providerLocation, setProviderLocation] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      claim_date: claimDate,
      claim_amount: Number(amount),
      claim_status: status,
      claim_type: type,
      claim_submission_method: method,
      diagnosis_code: diagnosisCode || null,
      procedure_code: procedureCode || null,
      provider_id: providerId || null,
      provider_specialty: providerSpecialty || null,
      provider_location: providerLocation || null,
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <FormField label="Claim date" name="claim_date" required error={fieldErrors.claim_date}>
        <input id="claim_date" type="date" value={claimDate}
               onChange={(e) => setClaimDate(e.target.value)} required />
      </FormField>
      <FormField label="Amount (USD)" name="claim_amount" required error={fieldErrors.claim_amount}>
        <input id="claim_amount" type="number" min="0" step="0.01" value={amount}
               onChange={(e) => setAmount(e.target.value)} required />
      </FormField>
      <FormField label="Claim type" name="claim_type" required error={fieldErrors.claim_type}>
        <select id="claim_type" value={type} onChange={(e) => setType(e.target.value as ClaimType)}>
          {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </FormField>
      <FormField label="Submission method" name="claim_submission_method" required
                 error={fieldErrors.claim_submission_method}>
        <select id="claim_submission_method" value={method}
                onChange={(e) => setMethod(e.target.value as ClaimMethod)}>
          {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </FormField>
      <FormField label="Status" name="claim_status" error={fieldErrors.claim_status}>
        <select id="claim_status" value={status}
                onChange={(e) => setStatus(e.target.value as ClaimStatus)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </FormField>
      <FormField label="Diagnosis code" name="diagnosis_code" optional error={fieldErrors.diagnosis_code}>
        <input id="diagnosis_code" value={diagnosisCode}
               onChange={(e) => setDiagnosisCode(e.target.value)} />
      </FormField>
      <FormField label="Procedure code" name="procedure_code" optional error={fieldErrors.procedure_code}>
        <input id="procedure_code" value={procedureCode}
               onChange={(e) => setProcedureCode(e.target.value)} />
      </FormField>
      <FormField label="Provider ID" name="provider_id" optional error={fieldErrors.provider_id}>
        <input id="provider_id" value={providerId}
               onChange={(e) => setProviderId(e.target.value)} />
      </FormField>
      <FormField label="Provider specialty" name="provider_specialty" optional
                 error={fieldErrors.provider_specialty}>
        <input id="provider_specialty" value={providerSpecialty}
               onChange={(e) => setProviderSpecialty(e.target.value)} />
      </FormField>
      <FormField label="Provider location" name="provider_location" optional
                 error={fieldErrors.provider_location}>
        <input id="provider_location" value={providerLocation}
               onChange={(e) => setProviderLocation(e.target.value)} />
      </FormField>
      <button type="submit" disabled={pending}>Save claim</button>
    </form>
  )
}
