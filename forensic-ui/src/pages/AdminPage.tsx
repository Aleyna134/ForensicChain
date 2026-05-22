import axios from 'axios'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { type AdminUser, type CreateUserBody, createUser, deleteUser, getUsers } from '../api/admin'
import {
  type Case, type CaseAssignment,
  createAssignment, createCase, deleteAssignment, deleteCase,
  listAdminCases, listAssignments, updateCaseStatus,
} from '../api/cases'
import Layout from '../components/Layout'

// ── Shared helpers ────────────────────────────────────────────────────────────

const ROLE_BADGE: Record<string, string> = {
  investigator:     'bg-blue-100   text-blue-700',
  forensic_analyst: 'bg-purple-100 text-purple-700',
  legal_reviewer:   'bg-orange-100 text-orange-700',
  admin:            'bg-red-100    text-red-700',
}

const CASE_STATUS_BADGE: Record<string, string> = {
  OPEN:   'bg-emerald-100 text-emerald-700',
  CLOSED: 'bg-slate-100   text-slate-500',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

function byCreatedDesc(a: AdminUser, b: AdminUser) {
  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
}

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-100 rounded animate-pulse w-24" />
        </td>
      ))}
    </tr>
  )
}

interface MenuAnchor { top: number; right: number }

// ── Add User Modal ────────────────────────────────────────────────────────────

function AddUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: (u: AdminUser) => void }) {
  const [form, setForm]     = useState<CreateUserBody>({ username: '', password: '', role: 'investigator' })
  const [error, setError]   = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const firstInput          = useRef<HTMLInputElement>(null)

  useEffect(() => { firstInput.current?.focus() }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true); setError(null)
    try {
      onCreated(await createUser(form))
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) setError('Username already exists.')
      else setError('Failed to create user. Please try again.')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-slate-800">Add New User</h2>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-600">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { label: 'Username', type: 'text',     key: 'username', ref: firstInput, placeholder: 'e.g. analyst02' },
            { label: 'Password', type: 'password', key: 'password', ref: undefined,  placeholder: '••••••••' },
          ].map(({ label, type, key, ref, placeholder }) => (
            <div key={key}>
              <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">{label}</label>
              <input ref={ref} required type={type}
                     value={key === 'username' ? form.username : form.password}
                     onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                     disabled={saving} placeholder={placeholder}
                     className="w-full rounded-lg border border-slate-200 px-3.5 py-2.5 text-sm
                                focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                                disabled:opacity-50 transition-all" />
            </div>
          ))}
          <div>
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">Role</label>
            <select value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                    disabled={saving}
                    className="w-full rounded-lg border border-slate-200 px-3.5 py-2.5 text-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                               disabled:opacity-50 transition-all">
              {[['investigator','Investigator'],['forensic_analyst','Forensic Analyst'],['legal_reviewer','Legal Reviewer']].map(([v,l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </div>
          {error && <p className="text-[11px] text-red-500">{error}</p>}
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} disabled={saving}
                    className="flex-1 py-2.5 rounded-lg border border-slate-200 text-sm font-medium
                               text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-colors">Cancel</button>
            <button type="submit" disabled={saving}
                    className="flex-1 py-2.5 rounded-lg bg-slate-800 text-sm font-semibold text-white
                               hover:bg-slate-700 disabled:opacity-50 transition-colors">
              {saving ? 'Adding…' : 'Add User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Add Case Modal ────────────────────────────────────────────────────────────

const CASE_RE = /^CASE-\d{4}-\d{3}$/

function AddCaseModal({ onClose, onCreated }: { onClose: () => void; onCreated: (c: Case) => void }) {
  const [caseNumber, setCaseNumber] = useState('')
  const [title,      setTitle]      = useState('')
  const [desc,       setDesc]       = useState('')
  const [error,      setError]      = useState<string | null>(null)
  const [saving,     setSaving]     = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!CASE_RE.test(caseNumber)) {
      setError('Format must be CASE-YYYY-NNN (e.g. CASE-2026-001)')
      return
    }
    setSaving(true); setError(null)
    try {
      onCreated(await createCase({ case_number: caseNumber, title, description: desc || undefined }))
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) setError('Case number already exists.')
      else setError('Failed to create case. Please try again.')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-slate-800">New Case</h2>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-600">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">Case Number</label>
            <input ref={inputRef} required value={caseNumber}
                   onChange={(e) => setCaseNumber(e.target.value.toUpperCase())}
                   placeholder="CASE-2026-001" disabled={saving}
                   className="w-full rounded-lg border border-slate-200 px-3.5 py-2.5 font-mono text-sm
                              focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                              disabled:opacity-50 transition-all" />
            <p className="mt-1 text-[11px] text-slate-400">Format: CASE-YYYY-NNN</p>
          </div>
          <div>
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">Title</label>
            <input required value={title} onChange={(e) => setTitle(e.target.value)}
                   placeholder="Brief case description" disabled={saving}
                   className="w-full rounded-lg border border-slate-200 px-3.5 py-2.5 text-sm
                              focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                              disabled:opacity-50 transition-all" />
          </div>
          <div>
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1.5">
              Description <span className="font-normal normal-case tracking-normal text-slate-400">(optional)</span>
            </label>
            <textarea rows={2} value={desc} onChange={(e) => setDesc(e.target.value)}
                      disabled={saving} placeholder="Additional context…"
                      className="w-full rounded-lg border border-slate-200 px-3.5 py-2.5 text-sm resize-none
                                 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                                 disabled:opacity-50 transition-all" />
          </div>
          {error && <p className="text-[11px] text-red-500">{error}</p>}
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} disabled={saving}
                    className="flex-1 py-2.5 rounded-lg border border-slate-200 text-sm font-medium
                               text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-colors">Cancel</button>
            <button type="submit" disabled={saving}
                    className="flex-1 py-2.5 rounded-lg bg-slate-800 text-sm font-semibold text-white
                               hover:bg-slate-700 disabled:opacity-50 transition-colors">
              {saving ? 'Creating…' : 'Create Case'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Assignments Modal ─────────────────────────────────────────────────────────

function AssignmentsModal({
  case: c,
  users,
  onClose,
}: {
  case: Case
  users: AdminUser[]
  onClose: () => void
}) {
  const [assignments, setAssignments] = useState<CaseAssignment[]>([])
  const [loading,     setLoading]     = useState(true)
  const [username,    setUsername]    = useState('')
  const [roleInCase,  setRoleInCase]  = useState('forensic_analyst')
  const [error,       setError]       = useState<string | null>(null)
  const [saving,      setSaving]      = useState(false)

  const assignableUsers = users.filter((u) => u.role !== 'admin' && u.is_active)

  useEffect(() => {
    listAssignments(c.id)
      .then(setAssignments)
      .catch(() => setError('Failed to load assignments.'))
      .finally(() => setLoading(false))
  }, [c.id])

  async function handleAssign(e: FormEvent) {
    e.preventDefault()
    if (!username) return
    setSaving(true); setError(null)
    try {
      const a = await createAssignment(c.id, { username, role_in_case: roleInCase })
      setAssignments((prev) => [...prev, a])
      setUsername('')
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) setError('User already assigned.')
      else setError('Failed to assign user.')
    } finally { setSaving(false) }
  }

  async function handleRemove(assignmentId: string) {
    try {
      await deleteAssignment(c.id, assignmentId)
      setAssignments((prev) => prev.filter((a) => a.id !== assignmentId))
    } catch {
      setError('Failed to remove assignment.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
         onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-base font-semibold text-slate-800">Assignments</h2>
          <button onClick={onClose} aria-label="Close" className="text-slate-400 hover:text-slate-600">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-slate-400 mb-5 font-mono">{c.case_number} — {c.title}</p>

        {/* Current assignments */}
        <div className="mb-5 rounded-lg border border-slate-200 overflow-hidden">
          <table className="w-full divide-y divide-slate-100">
            <thead>
              <tr className="bg-slate-50">
                {['Username', 'Role', 'Assigned', ''].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading
                ? Array.from({ length: 2 }).map((_, i) => <SkeletonRow key={i} cols={4} />)
                : assignments.length === 0
                  ? (
                    <tr>
                      <td colSpan={4} className="px-3 py-4 text-center text-xs text-slate-400">
                        No assignments yet.
                      </td>
                    </tr>
                  )
                  : assignments.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50">
                      <td className="px-3 py-2.5 text-sm font-mono text-slate-700">{a.username}</td>
                      <td className="px-3 py-2.5">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_BADGE[a.role_in_case] ?? 'bg-slate-100 text-slate-600'}`}>
                          {a.role_in_case}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-400">{formatDate(a.assigned_at)}</td>
                      <td className="px-3 py-2.5 text-right">
                        <button onClick={() => handleRemove(a.id)}
                                className="text-xs text-red-500 hover:text-red-700 transition-colors">
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>

        {/* Add assignment form */}
        <form onSubmit={handleAssign} className="flex gap-2 flex-wrap items-end">
          <div className="flex-1 min-w-[140px]">
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1">User</label>
            <select value={username} onChange={(e) => setUsername(e.target.value)}
                    disabled={saving}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                               disabled:opacity-50 transition-all">
              <option value="">Select user…</option>
              {assignableUsers.map((u) => (
                <option key={u.id} value={u.username}>{u.username} ({u.role})</option>
              ))}
            </select>
          </div>
          <div className="min-w-[160px]">
            <label className="block text-[10px] font-bold text-slate-500 tracking-[0.18em] uppercase mb-1">Role in Case</label>
            <select value={roleInCase} onChange={(e) => setRoleInCase(e.target.value)}
                    disabled={saving}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                               disabled:opacity-50 transition-all">
              <option value="investigator">Investigator</option>
              <option value="forensic_analyst">Forensic Analyst</option>
              <option value="legal_reviewer">Legal Reviewer</option>
            </select>
          </div>
          <button type="submit" disabled={saving || !username}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-sm font-semibold text-white
                             hover:bg-slate-700 disabled:opacity-50 transition-colors whitespace-nowrap">
            {saving ? 'Assigning…' : 'Assign'}
          </button>
        </form>

        {error && <p className="mt-2 text-[11px] text-red-500">{error}</p>}
      </div>
    </div>
  )
}

// ── Users Tab ─────────────────────────────────────────────────────────────────

function UsersTab() {
  const [users,      setUsers]      = useState<AdminUser[]>([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [openMenu,   setOpenMenu]   = useState<string | null>(null)
  const [menuAnchor, setMenuAnchor] = useState<MenuAnchor | null>(null)
  const [showModal,  setShowModal]  = useState(false)

  useEffect(() => {
    getUsers()
      .then((data) => setUsers([...data].sort(byCreatedDesc)))
      .catch(() => setError('Failed to load users.'))
      .finally(() => setLoading(false))
  }, [])

  function openMenuFor(e: React.MouseEvent<HTMLButtonElement>, id: string) {
    const r = e.currentTarget.getBoundingClientRect()
    const dropH = 44
    const fitsBelow = r.bottom + 4 + dropH < window.innerHeight
    setMenuAnchor({ top: fitsBelow ? r.bottom + 4 : r.top - dropH - 4, right: window.innerWidth - r.right })
    setOpenMenu(openMenu === id ? null : id)
  }

  async function handleDelete(id: string, username: string) {
    setOpenMenu(null)
    if (!window.confirm(`Delete "${username}"? This cannot be undone.`)) return
    try {
      await deleteUser(id)
      setUsers((prev) => prev.filter((u) => u.id !== id))
    } catch { alert('Failed to delete user.') }
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-slate-800">Users</h2>
          {!loading && !error && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
              {users.length}
            </span>
          )}
        </div>
        <button onClick={() => setShowModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800
                           text-xs font-semibold text-white hover:bg-slate-700 transition-colors">
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Add User
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>
      )}

      <div className="bg-white rounded-xl shadow-sm overflow-hidden w-full">
        <table className="w-full divide-y divide-slate-200">
          <thead>
            <tr className="bg-slate-50">
              {['Username', 'Role', 'Status', 'Created', ''].map((col) => (
                <th key={col} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-slate-800 font-mono">{u.username}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_BADGE[u.role] ?? 'bg-slate-100 text-slate-600'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${u.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={(e) => openMenuFor(e, u.id)}
                            className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors" aria-label="Actions">
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>

      {openMenu && menuAnchor && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpenMenu(null)} />
          <div className="fixed z-20 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1"
               style={{ top: menuAnchor.top, right: menuAnchor.right }}>
            <button onClick={() => { const u = users.find((u) => u.id === openMenu); if (u) handleDelete(u.id, u.username) }}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors">
              <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
                <path d="M10 11v6M14 11v6M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
              </svg>
              Delete user
            </button>
          </div>
        </>
      )}

      {showModal && <AddUserModal onClose={() => setShowModal(false)} onCreated={(u) => { setUsers((p) => [u, ...p]); setShowModal(false) }} />}
    </>
  )
}

// ── Cases Tab ─────────────────────────────────────────────────────────────────

function CasesTab({ users }: { users: AdminUser[] }) {
  const [cases,       setCases]       = useState<Case[]>([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState<string | null>(null)
  const [openMenu,    setOpenMenu]    = useState<string | null>(null)
  const [menuAnchor,  setMenuAnchor]  = useState<MenuAnchor | null>(null)
  const [showAdd,     setShowAdd]     = useState(false)
  const [assignCase,  setAssignCase]  = useState<Case | null>(null)

  useEffect(() => {
    listAdminCases()
      .then(setCases)
      .catch(() => setError('Failed to load cases.'))
      .finally(() => setLoading(false))
  }, [])

  function openMenuFor(e: React.MouseEvent<HTMLButtonElement>, id: string) {
    const r = e.currentTarget.getBoundingClientRect()
    const dropH = 88
    const fitsBelow = r.bottom + 4 + dropH < window.innerHeight
    setMenuAnchor({ top: fitsBelow ? r.bottom + 4 : r.top - dropH - 4, right: window.innerWidth - r.right })
    setOpenMenu(openMenu === id ? null : id)
  }

  async function handleDelete(id: string, caseNumber: string) {
    setOpenMenu(null)
    if (!window.confirm(`Delete case "${caseNumber}"? All assignments will be removed.`)) return
    try {
      await deleteCase(id)
      setCases((prev) => prev.filter((c) => c.id !== id))
    } catch { alert('Failed to delete case.') }
  }

  async function handleToggleStatus(c: Case) {
    setOpenMenu(null)
    const newStatus = c.status === 'OPEN' ? 'CLOSED' : 'OPEN'
    try {
      const updated = await updateCaseStatus(c.id, newStatus)
      setCases((prev) => prev.map((x) => x.id === c.id ? updated : x))
    } catch { alert('Failed to update case status.') }
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-slate-800">Cases</h2>
          {!loading && !error && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
              {cases.length}
            </span>
          )}
        </div>
        <button onClick={() => setShowAdd(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800
                           text-xs font-semibold text-white hover:bg-slate-700 transition-colors">
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New Case
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>
      )}

      <div className="bg-white rounded-xl shadow-sm overflow-hidden w-full">
        <table className="w-full divide-y divide-slate-200">
          <thead>
            <tr className="bg-slate-50">
              {['Case Number', 'Title', 'Status', 'Created', ''].map((col) => (
                <th key={col} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading
              ? Array.from({ length: 3 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              : cases.length === 0
                ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-400">
                      No cases yet. Create one to get started.
                    </td>
                  </tr>
                )
                : cases.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono font-medium text-slate-800">{c.case_number}</td>
                    <td className="px-4 py-3 text-sm text-slate-700 max-w-[200px] truncate" title={c.title}>{c.title}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${CASE_STATUS_BADGE[c.status] ?? 'bg-slate-100 text-slate-500'}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">{formatDate(c.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={(e) => openMenuFor(e, c.id)}
                              className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors" aria-label="Actions">
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                          <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))
            }
          </tbody>
        </table>
      </div>

      {openMenu && menuAnchor && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpenMenu(null)} />
          <div className="fixed z-20 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1"
               style={{ top: menuAnchor.top, right: menuAnchor.right }}>
            {(() => {
              const c = cases.find((x) => x.id === openMenu)
              if (!c) return null
              return (
                <>
                  <button onClick={() => { setOpenMenu(null); setAssignCase(c) }}
                          className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 transition-colors">
                    <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" /><circle cx="9" cy="7" r="4" />
                      <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
                    </svg>
                    Manage Assignments
                  </button>
                  <button onClick={() => handleToggleStatus(c)}
                          className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 transition-colors">
                    <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                      <path d="M18.364 5.636A9 9 0 115.636 18.364 9 9 0 0118.364 5.636z" />
                      <path d="M9 12l2 2 4-4" />
                    </svg>
                    {c.status === 'OPEN' ? 'Close Case' : 'Reopen Case'}
                  </button>
                  <button onClick={() => handleDelete(c.id, c.case_number)}
                          className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors">
                    <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6M10 11v6M14 11v6M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
                    </svg>
                    Delete Case
                  </button>
                </>
              )
            })()}
          </div>
        </>
      )}

      {showAdd && (
        <AddCaseModal
          onClose={() => setShowAdd(false)}
          onCreated={(c) => { setCases((prev) => [...prev, c]); setShowAdd(false) }}
        />
      )}

      {assignCase && (
        <AssignmentsModal
          case={assignCase}
          users={users}
          onClose={() => setAssignCase(null)}
        />
      )}
    </>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = 'users' | 'cases'

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('users')
  const [users, setUsers] = useState<AdminUser[]>([])

  useEffect(() => {
    getUsers().then(setUsers).catch(() => {})
  }, [])

  return (
    <Layout>
      <div className="h-full flex flex-col">

        {/* Header */}
        <div className="flex items-center gap-2 mb-5">
          <svg className="w-4 h-4 text-slate-400 flex-shrink-0" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
          <h1 className="text-xl font-semibold text-slate-800">Administration</h1>
        </div>

        {/* Tab navigation */}
        <div className="flex border-b border-slate-200 mb-6">
          {(['users', 'cases'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'border-slate-800 text-slate-800'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab === 'users' ? 'User Management' : 'Case Management'}
            </button>
          ))}
        </div>

        {activeTab === 'users'
          ? <UsersTab />
          : <CasesTab users={users} />
        }
      </div>
    </Layout>
  )
}
