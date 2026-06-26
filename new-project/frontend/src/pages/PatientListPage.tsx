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
      <div className="page-head">
        <h1>Patients</h1>
        {isAdmin && <Link className="button" to="/patients/new">Register patient</Link>}
      </div>
      <ErrorBanner error={error} />
      <table className="data-table">
        <thead><tr><th>Name</th><th>Gender</th><th>DOB</th>{isAdmin && <th></th>}</tr></thead>
        <tbody>
          {patients?.map((p) => (
            <tr key={p.id}>
              <td><Link to={`/patients/${p.id}`}>{p.name}</Link></td>
              <td>{p.gender}</td>
              <td>{p.date_of_birth}</td>
              {isAdmin && (
                <td>
                  <Link to={`/patients/${p.id}/edit`}>Edit</Link>{' '}
                  <button className="danger" onClick={() => setToDelete(p.id)}>Delete</button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
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
