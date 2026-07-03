import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useCreatePatient } from '../api/patients'
import { ApiError } from '../api/client'
import { getOcrStatus, extractPatientForm } from '../api/ocr'
import { useDismissOcrJob } from '../api/ocrJobs'
import PatientForm from '../components/PatientForm'
import ErrorBanner from '../components/ErrorBanner'
import type { PatientCreate } from '../api/types'

export default function PatientNewPage() {
  const create = useCreatePatient()
  const navigate = useNavigate()
  const location = useLocation()
  const navState = (location.state ?? {}) as { prefill?: Partial<PatientCreate>; jobId?: number }
  const dismissJob = useDismissOcrJob()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<unknown>(null)

  const [ocrAvailable, setOcrAvailable] = useState(false)
  const [ocrPending, setOcrPending] = useState(false)
  const [initial, setInitial] = useState<Partial<PatientCreate> | undefined>(navState.prefill)
  const [confidence, setConfidence] = useState<Record<string, number> | undefined>(undefined)
  const [formKey, setFormKey] = useState(0)

  useEffect(() => {
    getOcrStatus().then(setOcrAvailable).catch(() => setOcrAvailable(false))
  }, [])

  async function onUpload(file: File) {
    setOcrPending(true)
    setError(null)
    try {
      const result = await extractPatientForm(file)
      setInitial(result.fields)
      setConfidence(result.confidence)
      setFormKey((k) => k + 1)
    } catch (e) {
      setError(e)
    } finally {
      setOcrPending(false)
    }
  }

  return (
    <section>
      <ErrorBanner error={error} />
      {ocrAvailable && (
        <div className="card form-card ocr-upload">
          <label htmlFor="ocr-upload">Upload form (scan or photo) to auto-fill</label>
          <input
            id="ocr-upload"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={ocrPending}
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) onUpload(f)
            }}
          />
          {ocrPending && <span className="ocr-status">Reading form…</span>}
        </div>
      )}
      <PatientForm
        key={formKey}
        title="Register Patient"
        submitLabel="Create"
        pending={create.isPending}
        fieldErrors={fieldErrors}
        cancelTo="/patients"
        initial={initial}
        lowConfidence={confidence}
        onSubmit={async (data) => {
          setFieldErrors({}); setError(null)
          try {
            const p = await create.mutateAsync(data)
            if (navState.jobId != null) {
              try { await dismissJob.mutateAsync(navState.jobId) } catch { /* job already gone is fine */ }
            }
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
