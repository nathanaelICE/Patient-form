import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreatePatient } from '../api/patients'
import { ApiError } from '../api/client'
import PatientForm from '../components/PatientForm'
import ErrorBanner from '../components/ErrorBanner'

export default function PatientNewPage() {
  const create = useCreatePatient()
  const navigate = useNavigate()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<unknown>(null)

  return (
    <section>
      <ErrorBanner error={error} />
      <PatientForm
        title="Register Patient"
        submitLabel="Create"
        pending={create.isPending}
        fieldErrors={fieldErrors}
        cancelTo="/patients"
        onSubmit={async (data) => {
          setFieldErrors({}); setError(null)
          try {
            const p = await create.mutateAsync(data)
            navigate(`/patients/${p.id}`)
          } catch (e) {
            if (e instanceof ApiError && e.status === 422) setFieldErrors(e.fieldErrors())
            else setError(e)
          }
        }}
      />
    </section>
  )
}
