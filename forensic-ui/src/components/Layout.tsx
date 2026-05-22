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
  { to: '/admin/users',      label: 'User Management',  roles: ['admin'] },
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
        <div className="px-5 py-4 border-b border-slate-700 flex items-center gap-2.5">
          <svg className="w-7 h-7 flex-shrink-0" viewBox="0 0 28 28" fill="none">
            {/* Shield — heraldic pointed base */}
            <path
              d="M14 2.5L4.5 6.5V14c0 6 4.2 11 9.5 12.5C19.3 25 23.5 20 23.5 14V6.5L14 2.5z"
              fill="url(#shield-fill)" stroke="url(#shield-stroke)" strokeWidth="1.6"
              strokeLinejoin="round"
            />
            {/* Top chain block */}
            <rect x="10.5" y="8.5" width="7" height="4.5" rx="2"
              fill="none" stroke="#93c5fd" strokeWidth="1.5"
            />
            {/* Chain connector */}
            <line x1="14" y1="13" x2="14" y2="15.5"
              stroke="#93c5fd" strokeWidth="1.6" strokeLinecap="round"
            />
            {/* Bottom chain block */}
            <rect x="10.5" y="15.5" width="7" height="4.5" rx="2"
              fill="none" stroke="#93c5fd" strokeWidth="1.5"
            />
            {/* Small dot in each block — "sealed" indicator */}
            <circle cx="14" cy="10.75" r="0.8" fill="#bfdbfe" />
            <circle cx="14" cy="17.75" r="0.8" fill="#bfdbfe" />
            <defs>
              <linearGradient id="shield-fill" x1="14" y1="2.5" x2="14" y2="27" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.22" />
                <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.08" />
              </linearGradient>
              <linearGradient id="shield-stroke" x1="14" y1="2.5" x2="14" y2="27" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#93c5fd" />
                <stop offset="100%" stopColor="#60a5fa" />
              </linearGradient>
            </defs>
          </svg>
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
