import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface NavItem {
  to: string
  label: string
  roles: string[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/',                 label: 'Dashboard',        roles: ['investigator', 'forensic_analyst', 'legal_reviewer', 'admin'] },
  { to: '/artifacts/upload', label: 'Upload Evidence',  roles: ['investigator', 'forensic_analyst'] },
  { to: '/artifacts',        label: 'My Artifacts',     roles: ['investigator'] },
  { to: '/artifacts',        label: 'Evidence List',    roles: ['forensic_analyst'] },
  { to: '/artifacts',        label: 'Evidence List',    roles: ['legal_reviewer'] },
  { to: '/ledger',           label: 'Ledger Chain',     roles: ['legal_reviewer'] },
  { to: '/admin/users',      label: 'Management Panel',  roles: ['admin'] },
]

interface Props {
  children: ReactNode
}

export default function Layout({ children }: Props) {
  const { username, role, logout } = useAuth()
  const { pathname } = useLocation()

  const visibleNav = NAV_ITEMS.filter((item) => role && item.roles.includes(role))
  const initial = (username ?? '?').charAt(0).toUpperCase()

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">

      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside className="w-56 flex-shrink-0 flex flex-col bg-slate-800 text-slate-100">

        {/* Wordmark */}
        <div className="px-5 py-4 border-b border-slate-700 flex items-center gap-0">
          <img src="/fc-logo.svg" alt="ForensicChain" className="w-11 h-11 flex-shrink-0 object-contain" />
          <span className="font-bold text-base tracking-tight">ForensicChain</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {visibleNav.map(({ to, label }) => {
            const isActive = pathname === to
            return (
              <Link
                key={label}
                to={to}
                className={`block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-300 hover:bg-slate-700/60 hover:text-white'
                }`}
                style={isActive ? { boxShadow: 'inset 3px 0 0 #60a5fa' } : {}}
              >
                {label}
              </Link>
            )
          })}
        </nav>

        {/* User section */}
        <div className="px-4 py-4 border-t border-slate-700/60">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center
                            text-xs font-bold text-white flex-shrink-0">
              {initial}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">{username ?? '—'}</p>
              <p className="text-xs text-slate-500 truncate">{role}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full rounded-md py-1.5 text-xs text-slate-400
                       hover:text-white hover:bg-slate-700 transition-colors text-center"
          >
            Sign out
          </button>
        </div>

      </aside>

      {/* ── Main ─────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
