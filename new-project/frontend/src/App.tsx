import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ProtectedRoute from './auth/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import PatientListPage from './pages/PatientListPage'
import PatientNewPage from './pages/PatientNewPage'
import PatientDetailPage from './pages/PatientDetailPage'
import PatientEditPage from './pages/PatientEditPage'
import VisitNewPage from './pages/VisitNewPage'
import VisitEditPage from './pages/VisitEditPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/patients" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/patients" element={<PatientListPage />} />
        <Route path="/patients/:id" element={<PatientDetailPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/patients/new" element={<PatientNewPage />} />
          <Route path="/patients/:id/edit" element={<PatientEditPage />} />
          <Route path="/patients/:id/visits/new" element={<VisitNewPage />} />
          <Route path="/patients/:id/visits/:vid/edit" element={<VisitEditPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
