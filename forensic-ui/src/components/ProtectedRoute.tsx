import { Navigate, Outlet } from 'react-router-dom'
import { getRole, hasRole, isAuthenticated } from '../hooks/useAuth'

interface Props {
  allowedRoles?: string[]
}

export default function ProtectedRoute({ allowedRoles }: Props) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  if (allowedRoles && !hasRole(allowedRoles)) {
    // Send admin to their own home instead of the generic 403 page
    if (getRole() === 'admin') return <Navigate to="/admin/users" replace />
    return <Navigate to="/unauthorized" replace />
  }
  return <Outlet />
}
