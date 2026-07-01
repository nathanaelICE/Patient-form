import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { usePatient } from '../api/patients'
import { useVisits, useDeleteVisit } from '../api/visits'
import { useClaims, useCreateClaim, useDeleteClaim } from '../api/claims'
import { useAuth } from '../auth/AuthContext'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorBanner from '../components/ErrorBanner'
import ClaimForm from '../components/ClaimForm'
import { ApiError } from '../api/client'

export default function PatientDetailPage() {
  const { id } = useParams()
  const patientId = Number(id)
  const { data: patient, isLoading, error } = usePatient(patientId)
  const { data: visits } = useVisits(patientId)
  const delVisit = useDeleteVisit(patientId)
  const { data: claims } = useClaims(patientId)
  const createClaim = useCreateClaim(patientId)
  const deleteClaim = useDeleteClaim(patientId)
  const { isAdmin } = useAuth()
  const [toDelete, setToDelete] = useState<number | null>(null)
  const [claimToDelete, setClaimToDelete] = useState<number | null>(null)
  const [claimFormKey, setClaimFormKey] = useState(0)
  const [claimErrors, setClaimErrors] = useState<Record<string, string>>({})

  if (isLoading) return <p>Loading…</p>
  if (error) return <ErrorBanner error={error} />
  if (!patient) return <p>Patient not found.</p>

  return (
    <section>
      <Link to="/patients" className="back-link">← Back to list</Link>

      <section className="card">
        <div className="section-header">
          <h2 className="section-title">Patient Information</h2>
          {isAdmin && <Link className="btn btn-secondary" to={`/patients/${patientId}/edit`}>✎ Edit</Link>}
        </div>
        <dl className="info-grid">
          <dt>Name</dt><dd>{patient.name}</dd>
          <dt>Date of Birth</dt><dd>{patient.date_of_birth}</dd>
          <dt>Gender</dt><dd>{patient.gender}</dd>
          <dt>Phone</dt><dd>{patient.phone || <span className="placeholder">—</span>}</dd>
        </dl>
      </section>

      <section className="card">
        <div className="section-header">
          <h2 className="section-title">Visit History</h2>
          {isAdmin && <Link className="btn btn-primary" to={`/patients/${patientId}/visits/new`}>+ Add Visit</Link>}
        </div>
        <div className="table-wrapper">
          {visits && visits.length > 0 ? (
            <table className="visit-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Chief Complaint</th>
                  <th>Diagnosis</th>
                  <th>Notes</th>
                  {isAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {visits.map((v) => (
                  <tr key={v.id}>
                    <td>{v.date}</td>
                    <td>{v.chief_complaint}</td>
                    <td>{v.diagnosis || '-'}</td>
                    <td>{v.notes || '-'}</td>
                    {isAdmin && (
                      <td className="actions-cell">
                        <Link to={`/patients/${patientId}/visits/${v.id}/edit`} className="btn btn-secondary btn-icon" title="Edit">✎</Link>
                        <button className="btn btn-danger btn-icon" title="Delete" onClick={() => setToDelete(v.id)}>🗑</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="empty-state">No visits recorded yet.</p>
          )}
        </div>
      </section>

      <section className="card">
        <div className="section-header">
          <h2 className="section-title">Claims</h2>
        </div>
        <ul>
          {claims?.map((c) => (
            <li key={c.id}>
              {c.claim_date} — {c.claim_type} — ${c.claim_amount} — {c.claim_status}
              {isAdmin && (
                <button onClick={() => setClaimToDelete(c.id)}>Delete</button>
              )}
            </li>
          ))}
        </ul>
        {isAdmin && (
          <ClaimForm
            key={claimFormKey}
            pending={createClaim.isPending}
            fieldErrors={claimErrors}
            onSubmit={(body) => {
              setClaimErrors({})
              createClaim.mutate(body, {
                onSuccess: () => setClaimFormKey(k => k + 1),
                onError: (err) => {
                  if (err instanceof ApiError) setClaimErrors(err.fieldErrors())
                },
              })
            }}
          />
        )}
      </section>

      <ConfirmDialog
        open={toDelete !== null}
        title="Delete visit"
        message="Permanently delete this visit?"
        onCancel={() => setToDelete(null)}
        onConfirm={() => { if (toDelete !== null) delVisit.mutate(toDelete); setToDelete(null) }}
      />
      <ConfirmDialog
        open={claimToDelete !== null}
        title="Delete claim"
        message="Delete this claim? This cannot be undone."
        onCancel={() => setClaimToDelete(null)}
        onConfirm={() => { if (claimToDelete !== null) deleteClaim.mutate(claimToDelete); setClaimToDelete(null) }}
      />
    </section>
  )
}
