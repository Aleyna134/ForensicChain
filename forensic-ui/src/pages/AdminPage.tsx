import axios from 'axios'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { type AdminUser, type CreateUserBody, createUser, deleteUser, getUsers } from '../api/admin'
import Layout from '../components/Layout'

// ── Constants ─────────────────────────────────────────────────────────────────

const ROLE_OPTIONS = [
  { value: 'investigator',     label: 'Investigator' },
  { value: 'forensic_analyst', label: 'Forensic Analyst' },
  { value: 'legal_reviewer',   label: 'Legal Reviewer' },
]

const ROLE_BADGE: Record<string, string> = {
  investigator:     'bg-blue-100   text-blue-700',
  forensic_analyst: 'bg-purple-100 text-purple-700',
  legal_reviewer:   'bg-orange-100 text-orange-700',
  admin:            'bg-red-100    text-red-700',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

function byCreatedDesc(a: AdminUser, b: AdminUser) {
  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr>
      {['w-32', 'w-24', 'w-16', 'w-24', 'w-4'].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className={`h-4 bg-slate-100 rounded animate-pulse ${w}`} />
        </td>
      ))}
    </tr>
  )
}

// ── Add User Modal ────────────────────────────────────────────────────────────

interface AddUserModalProps {
  onClose: () => void
  onCreated: (user: AdminUser) => void
}

function AddUserModal({ onClose, onCreated }: AddUserModalProps) {
  const [form, setForm]     = useState<CreateUserBody>({ username: '', password: '', role: 'investigator' })
  const [error, setError]   = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const firstInput          = useRef<HTMLInputElement>(null)

  useEffect(() => { firstInput.current?.focus() }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const user = await createUser(form)
      onCreated(user)
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setError('Username already exists.')
      } else {
        setError('Failed to create user. Please try again.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">

        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-slate-800">Add New User</h2>
          <button onClick={onClose} aria-label="Close"
                  className="text-slate-400 hover:text-slate-600 transition-colors">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">
              Username
            </label>
            <input
              ref={firstInput}
              required
              type="text"
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              disabled={saving}
              placeholder="e.g. investigator02"
              className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5
                         font-mono text-sm text-slate-800 placeholder-slate-400
                         focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                         disabled:opacity-50 transition-all"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">
              Password
            </label>
            <input
              required
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              disabled={saving}
              placeholder="••••••••"
              className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5
                         text-sm text-slate-800 placeholder-slate-400
                         focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                         disabled:opacity-50 transition-all"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">
              Role
            </label>
            <select
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              disabled={saving}
              className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5
                         text-sm text-slate-800
                         focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                         disabled:opacity-50 transition-all"
            >
              {ROLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="flex items-center gap-1.5 text-[11px] text-red-500">
              <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
              </svg>
              {error}
            </p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button" onClick={onClose} disabled={saving}
              className="flex-1 py-2.5 rounded-lg border border-slate-200 text-sm font-medium
                         text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit" disabled={saving}
              className="flex-1 py-2.5 rounded-lg bg-slate-800 text-sm font-semibold text-white
                         hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Adding…' : 'Add User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

interface MenuAnchor { top: number; right: number }

export default function AdminPage() {
  const [users,      setUsers]      = useState<AdminUser[]>([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [openMenu,   setOpenMenu]   = useState<string | null>(null)
  const [menuAnchor, setMenuAnchor] = useState<MenuAnchor | null>(null)
  const [showModal,  setShowModal]  = useState(false)

  useEffect(() => {
    getUsers()
      .then((data) => setUsers([...data].sort(byCreatedDesc)))
      .catch(() => setError('Failed to load users. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  function handleCreated(user: AdminUser) {
    setUsers((prev) => [user, ...prev])
    setShowModal(false)
  }

  function openMenuFor(e: React.MouseEvent<HTMLButtonElement>, id: string) {
    const r       = e.currentTarget.getBoundingClientRect()
    const dropH   = 44
    const fitsBelow = r.bottom + 4 + dropH < window.innerHeight
    setMenuAnchor({
      top:   fitsBelow ? r.bottom + 4 : r.top - dropH - 4,
      right: window.innerWidth - r.right,
    })
    setOpenMenu(openMenu === id ? null : id)
  }

  async function handleDelete(id: string, username: string) {
    setOpenMenu(null)
    if (!window.confirm(`Delete "${username}"? This cannot be undone.`)) return
    try {
      await deleteUser(id)
      setUsers((prev) => prev.filter((u) => u.id !== id))
    } catch {
      alert('Failed to delete user. Please try again.')
    }
  }

  return (
    <Layout>
      <div className="h-full flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            <h1 className="text-xl font-semibold text-slate-800">User Management</h1>
            {!loading && !error && (
              <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded-full
                               text-xs font-medium bg-slate-100 text-slate-600">
                {users.length} {users.length === 1 ? 'user' : 'users'}
              </span>
            )}
          </div>

          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800
                       text-xs font-semibold text-white hover:bg-slate-700 transition-colors"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Add User
          </button>
        </div>
        <p className="text-xs text-slate-400 mb-6">Full user management coming soon</p>

        {/* Error */}
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200
                          bg-red-50 px-4 py-3 text-sm text-red-600">
            <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
            </svg>
            {error}
          </div>
        )}

        {/* Table — fills remaining width */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden w-full">
          <table className="w-full divide-y divide-slate-200">
            <thead>
              <tr className="bg-slate-50">
                {['Username', 'Role', 'Status', 'Created', ''].map((col) => (
                  <th key={col}
                      className="px-4 py-3 text-left text-xs font-semibold text-slate-500
                                 uppercase tracking-wider">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading
                ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)
                : users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-slate-800 font-mono">
                      {u.username}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium
                                       ${ROLE_BADGE[u.role] ?? 'bg-slate-100 text-slate-600'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.is_active
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-500'
                      }`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">
                      {formatDate(u.created_at)}
                    </td>

                    {/* Three-dot menu — uses fixed positioning to escape overflow:hidden */}
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => openMenuFor(e, u.id)}
                        className="p-1 rounded text-slate-400 hover:text-slate-600
                                   hover:bg-slate-100 transition-colors"
                        aria-label="Actions"
                      >
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                          <circle cx="12" cy="5"  r="1.5" />
                          <circle cx="12" cy="12" r="1.5" />
                          <circle cx="12" cy="19" r="1.5" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>

      </div>

      {/* Fixed dropdown — rendered outside the overflow:hidden table wrapper */}
      {openMenu && menuAnchor && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpenMenu(null)} />
          <div
            className="fixed z-20 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1"
            style={{ top: menuAnchor.top, right: menuAnchor.right }}
          >
            <button
              onClick={() => {
                const user = users.find((u) => u.id === openMenu)
                if (user) handleDelete(user.id, user.username)
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-600
                         hover:bg-red-50 flex items-center gap-2 transition-colors"
            >
              <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
                <path d="M10 11v6M14 11v6" />
                <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
              </svg>
              Delete user
            </button>
          </div>
        </>
      )}

      {showModal && (
        <AddUserModal
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}
    </Layout>
  )
}
