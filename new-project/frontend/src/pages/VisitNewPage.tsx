import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useCreateVisit } from '../api/visits'
import { ApiError } from '../api/client'
import VisitForm from '../components/VisitForm'
import ErrorBanner from '../components/ErrorBanner'

export default function VisitNewPage() {
  const { id } = useParams()
  const patientId = Number(id)
  const create = useCreateVisit(patientId)
  const navigate = useNavigate()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<unknown>(null)

  return (
    <section>
      <ErrorBanner error={error} />
      <VisitForm
        title="Add Visit"
        submitLabel="Create"
        pending={create.isPending}
        fieldErrors={fieldErrors}
        cancelTo={`/patients/${patientId}`}
        onSubmit={async (data) => {
          setFieldErrors({}); setError(null)
          try {
            await create.mutateAsync(data)
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
