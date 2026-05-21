import { Link } from 'react-router-dom'
import { getRole, getUsername } from '../hooks/useAuth'

export default function UnauthorizedPage() {
  const username = getUsername()
  const role = getRole()

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="text-center space-y-3">
        <div className="text-6xl font-bold text-red-500">403</div>
        <h1 className="text-xl font-semibold text-white">
          You do not have permission to access this page
        </h1>
        {username && (
          <p className="text-sm text-slate-400">
            Kullanıcı:{' '}
            <span className="text-slate-200 font-medium">{username}</span>
          </p>
        )}
        {role && (
          <p className="text-sm text-slate-400">
            Rol:{' '}
            <span className="text-indigo-400 font-medium">{role}</span>
          </p>
        )}
        <div className="pt-2">
          <Link
            to="/"
            className="inline-block rounded-md bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
          >
            Dashboard'a dön
          </Link>
        </div>
      </div>
    </div>
  )
}
