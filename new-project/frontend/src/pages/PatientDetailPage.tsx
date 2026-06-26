import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { usePatient } from '../api/patients'
import { useVisits, useDeleteVisit } from '../api/visits'
import { useAuth } from '../auth/AuthContext'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorBanner from '../components/ErrorBanner'

export default function PatientDetailPage() {
  const { id } = useParams()
  const patientId = Number(id)
  const { data: patient, isLoading, error } = usePatient(patientId)
  const { data: visits } = useVisits(patientId)
  const delVisit = useDeleteVisit(patientId)
  const { isAdmin } = useAuth()
  const [toDelete, setToDelete] = useState<number | null>(null)

  if (isLoading) return <p>Loading…</p>
  if (error) return <ErrorBanner error={error} />
  if (!patient) return <p>Patient not found.</p>

  return (
    <section>
      <div className="page-head">
        <h1>{patient.name}</h1>
        {isAdmin && <Link className="button" to={`/patients/${patientId}/edit`}>Edit</Link>}
      </div>
      <dl className="details">
        <dt>Gender</dt><dd>{patient.gender}</dd>
        <dt>Date of birth</dt><dd>{patient.date_of_birth}</dd>
        <dt>Phone</dt><dd>{patient.phone ?? '—'}</dd>
      </dl>

      <div className="page-head">
        <h2>Visits</h2>
        {isAdmin && <Link className="button" to={`/patients/${patientId}/visits/new`}>Add visit</Link>}
      </div>
      <table className="data-table">
        <thead><tr><th>Date</th><th>Chief complaint</th><th>Diagnosis</th>{isAdmin && <th></th>}</tr></thead>
        <tbody>
          {visits?.map((v) => (
            <tr key={v.id}>
              <td>{v.date}</td>
              <td>{v.chief_complaint}</td>
              <td>{v.diagnosis ?? '—'}</td>
              {isAdmin && (
                <td>
                  <Link to={`/patients/${patientId}/visits/${v.id}/edit`}>Edit</Link>{' '}
                  <button className="danger" onClick={() => setToDelete(v.id)}>Delete</button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      <ConfirmDialog
        open={toDelete !== null}
        title="Delete visit"
        message="Permanently delete this visit?"
        onCancel={() => setToDelete(null)}
        onConfirm={() => { if (toDelete !== null) delVisit.mutate(toDelete); setToDelete(null) }}
      />
    </section>
  )
}
