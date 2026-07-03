import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { usePatients, useDeletePatient } from '../api/patients'
import { useOcrJobs, useUploadOcrJobs, useRetryOcrJob, useDismissOcrJob } from '../api/ocrJobs'
import { getOcrStatus } from '../api/ocr'
import { useAuth } from '../auth/AuthContext'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorBanner from '../components/ErrorBanner'

export default function PatientListPage() {
  const { data: patients, isLoading, error } = usePatients()
  const del = useDeletePatient()
  const { isAdmin } = useAuth()
  const navigate = useNavigate()
  const [toDelete, setToDelete] = useState<number | null>(null)

  const [ocrAvailable, setOcrAvailable] = useState(false)
  useEffect(() => {
    if (isAdmin) getOcrStatus().then(setOcrAvailable).catch(() => setOcrAvailable(false))
  }, [isAdmin])

  const jobs = useOcrJobs(isAdmin)
  const upload = useUploadOcrJobs()
  const retry = useRetryOcrJob()
  const dismiss = useDismissOcrJob()

  const allJobs = jobs.data ?? []
  const processing = allJobs.filter((j) => j.status === 'pending' || j.status === 'processing')
  const errored = allJobs.filter((j) => j.status === 'error')
  const colSpan = isAdmin ? 6 : 5

  if (isLoading) return <p>Loading…</p>
  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">Patients</h2>
        {isAdmin && <Link className="btn btn-primary" to="/patients/new">+ Register Patient</Link>}
      </div>
      <ErrorBanner error={error} />
      {isAdmin && ocrAvailable && (
        <div className="card form-card ocr-upload">
          <label htmlFor="ocr-batch">Upload one or more forms to auto-register patients</label>
          <input
            id="ocr-batch"
            type="file"
            multiple
            accept="image/png,image/jpeg,image/webp"
            disabled={upload.isPending}
            onChange={(e) => {
              const files = Array.from(e.target.files ?? [])
              if (files.length) upload.mutate(files)
              e.target.value = ''
            }}
          />
          {upload.isPending && <span className="ocr-status">Uploading…</span>}
          <ErrorBanner error={upload.error} />
        </div>
      )}
      <div className="table-wrapper">
        <table className="patient-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Gender</th>
              <th>Phone</th>
              <th>Date of Birth</th>
              {isAdmin && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {processing.map((j) => (
              <tr key={`job-${j.id}`} className="ocr-row ocr-row-processing">
                <td>—</td>
                <td>{j.filename}</td>
                <td colSpan={colSpan - 2}>Processing…</td>
              </tr>
            ))}
            {(patients ?? []).map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td><Link to={`/patients/${p.id}`}>{p.name}</Link></td>
                <td>{p.gender}</td>
                <td>{p.phone || '-'}</td>
                <td>{p.date_of_birth}</td>
                {isAdmin && (
                  <td className="actions-cell">
                    <Link to={`/patients/${p.id}/edit`} className="btn btn-secondary btn-icon" title="Edit">✎</Link>
                    <button className="btn btn-danger btn-icon" title="Delete" onClick={() => setToDelete(p.id)}>🗑</button>
                  </td>
                )}
              </tr>
            ))}
            {isAdmin && errored.map((j) => (
              <tr key={`job-${j.id}`} className="ocr-row ocr-row-error">
                <td><strong>ERROR</strong></td>
                <td>{j.filename}</td>
                <td colSpan={colSpan - 3}>{j.error_message || 'could not read document'}</td>
                <td className="actions-cell">
                  <button className="btn btn-secondary" onClick={() => retry.mutate(j.id)}>Retry</button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => navigate('/patients/new', { state: { prefill: j.extracted_fields ?? {}, jobId: j.id } })}
                  >Manual entry</button>
                  <button className="btn btn-danger" onClick={() => dismiss.mutate(j.id)}>Dismiss</button>
                </td>
              </tr>
            ))}
            {(patients?.length ?? 0) === 0 && allJobs.length === 0 && (
              <tr><td colSpan={colSpan} className="empty-state">No patients registered yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <ConfirmDialog
        open={toDelete !== null}
        title="Delete patient"
        message="This soft-deletes the patient. Continue?"
        onCancel={() => setToDelete(null)}
        onConfirm={() => { if (toDelete !== null) del.mutate(toDelete); setToDelete(null) }}
      />
    </section>
  )
}
