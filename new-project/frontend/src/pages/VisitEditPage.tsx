import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useVisits, useUpdateVisit } from '../api/visits'
import { ApiError } from '../api/client'
import VisitForm from '../components/VisitForm'
import ErrorBanner from '../components/ErrorBanner'

export default function VisitEditPage() {
  const { id, vid } = useParams()
  const patientId = Number(id)
  const visitId = Number(vid)
  const { data: visits, isLoading } = useVisits(patientId)
  const update = useUpdateVisit(patientId, visitId)
  const navigate = useNavigate()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<unknown>(null)

  if (isLoading) return <p>Loading…</p>
  const visit = visits?.find((v) => v.id === visitId)
  if (!visit) return <p>Visit not found.</p>

  return (
    <section>
      <ErrorBanner error={error} />
      <VisitForm
        title="Edit Visit"
        initial={visit}
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
