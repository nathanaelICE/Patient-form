import { useState } from 'react'
import { Link } from 'react-router-dom'
import { usePatients, useDeletePatient } from '../api/patients'
import { useAuth } from '../auth/AuthContext'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorBanner from '../components/ErrorBanner'

export default function PatientListPage() {
  const { data: patients, isLoading, error } = usePatients()
  const del = useDeletePatient()
  const { isAdmin } = useAuth()
  const [toDelete, setToDelete] = useState<number | null>(null)

  if (isLoading) return <p>Loading…</p>
  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">Patients</h2>
        {isAdmin && <Link className="btn btn-primary" to="/patients/new">+ Register Patient</Link>}
      </div>
      <ErrorBanner error={error} />
      <div className="table-wrapper">
        {patients && patients.length > 0 ? (
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
              {patients.map((p) => (
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
            </tbody>
          </table>
        ) : (
          <p className="empty-state">No patients registered yet.</p>
        )}
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
