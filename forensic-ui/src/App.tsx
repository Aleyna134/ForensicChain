import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import AdminPage from './pages/AdminPage'
import ArtifactDetailPage from './pages/ArtifactDetailPage'
import ArtifactListPage from './pages/ArtifactListPage'
import ArtifactUploadPage from './pages/ArtifactUploadPage'
import CasesPage from './pages/CasesPage'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import ReportPage from './pages/ReportPage'
import UnauthorizedPage from './pages/UnauthorizedPage'
import { getRole, isAuthenticated } from './hooks/useAuth'

// Redirects to the role's home page — used by the catch-all route
function RoleHome() {
  if (!isAuthenticated()) return <Navigate to="/login" replace />
  return <Navigate to={getRole() === 'admin' ? '/admin/users' : '/'} replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ── Public ────────────────────────────────────────────────── */}
        <Route path="/login"        element={<LoginPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        {/* ── investigator + forensic_analyst + legal_reviewer ──────── */}
        <Route element={<ProtectedRoute allowedRoles={['investigator', 'forensic_analyst', 'legal_reviewer']} />}>
          <Route path="/"               element={<DashboardPage />} />
          <Route path="/cases/:caseId"  element={<CasesPage />} />
        </Route>

        {/* ── investigator + forensic_analyst ───────────────────────── */}
        <Route element={<ProtectedRoute allowedRoles={['investigator', 'forensic_analyst']} />}>
          <Route path="/artifacts/upload" element={<ArtifactUploadPage />} />
        </Route>

        {/* ── investigator + forensic_analyst ───────────────────────── */}
        <Route element={<ProtectedRoute allowedRoles={['investigator', 'forensic_analyst']} />}>
          <Route path="/artifacts"     element={<ArtifactListPage />} />
          <Route path="/artifacts/:id" element={<ArtifactDetailPage />} />
        </Route>

        {/* ── forensic_analyst + legal_reviewer ─────────────────────── */}
        <Route element={<ProtectedRoute allowedRoles={['forensic_analyst', 'legal_reviewer']} />}>
          <Route path="/custody/:artifactId" element={<CasesPage />} />
        </Route>

        {/* ── legal_reviewer only ────────────────────────────────────── */}
        <Route element={<ProtectedRoute allowedRoles={['legal_reviewer']} />}>
          <Route path="/reports/:artifactId" element={<ReportPage />} />
        </Route>

        {/* ── admin only ─────────────────────────────────────────────── */}
        <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
          <Route path="/admin/users" element={<AdminPage />} />
        </Route>

        <Route path="*" element={<RoleHome />} />
      </Routes>
    </BrowserRouter>
  )
}
