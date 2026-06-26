import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { usePatient, useUpdatePatient } from '../api/patients'
import { ApiError } from '../api/client'
import PatientForm from '../components/PatientForm'
import ErrorBanner from '../components/ErrorBanner'

export default function PatientEditPage() {
  const { id } = useParams()
  const patientId = Number(id)
  const { data: patient, isLoading } = usePatient(patientId)
  const update = useUpdatePatient(patientId)
  const navigate = useNavigate()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<unknown>(null)

  if (isLoading) return <p>Loading…</p>
  if (!patient) return <p>Patient not found.</p>

  return (
    <section>
      <ErrorBanner error={error} />
      <PatientForm
        title="Edit Patient"
        initial={patient}
        submitLabel="Save Changes"
        pending={update.isPending}
        fieldErrors={fieldErrors}
        cancelTo={`/patients/${patientId}`}
        onSubmit={async (data) => {
          setFieldErrors({}); setError(null)
          try {
            await update.mutateAsync(data)
            navigate(`/patients/${patientId}`)
          } catch (e) {
            if (e instanceof ApiError && e.status === 422) setFieldErrors(e.fieldErrors())
            else setError(e)
          }
        }}
      />
    </section>
  )
}
