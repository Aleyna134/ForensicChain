import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listArtifacts, type Artifact } from '../api/evidence'
import { listCases, listAdminCases, type Case } from '../api/cases'
import Layout from '../components/Layout'
import { useAuth } from '../hooks/useAuth'

const ROLE_META: Record<string, { label: string; badge: string; tip: string }> = {
  investigator: {
    label: 'Investigator',
    badge: 'bg-blue-100 text-blue-700',
    tip: 'All uploaded artifacts are automatically hashed and signed. Once ingested, they cannot be altered.',
  },
  forensic_analyst: {
    label: 'Forensic Analyst',
    badge: 'bg-violet-100 text-violet-700',
    tip: 'Use Verify Integrity on any artifact to confirm its cryptographic hash and ledger chain status.',
  },
  legal_reviewer: {
    label: 'Legal Reviewer',
    badge: 'bg-amber-100 text-amber-700',
    tip: 'Open any artifact to generate a signed PDF audit report suitable for legal proceedings.',
  },
  admin: {
    label: 'Administrator',
    badge: 'bg-slate-100 text-slate-700',
    tip: 'Manage cases, create user accounts, and assign personnel to investigations.',
  },
}

const TIP_COLORS: Record<string, string> = {
  investigator:   'border-blue-100 bg-blue-50 text-blue-700',
  forensic_analyst: 'border-violet-100 bg-violet-50 text-violet-700',
  legal_reviewer: 'border-amber-100 bg-amber-50 text-amber-700',
  admin:          'border-slate-200 bg-slate-50 text-slate-600',
}

function RoleVisual({ role }: { role: string | null }) {
  if (role === 'investigator') return (
    <div className="w-14 h-14 rounded-2xl bg-blue-100 flex items-center justify-center flex-shrink-0">
      <svg className="w-7 h-7 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </svg>
    </div>
  )
  if (role === 'forensic_analyst') return (
    <div className="w-14 h-14 rounded-2xl bg-violet-100 flex items-center justify-center flex-shrink-0">
      <svg className="w-7 h-7 text-violet-500" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    </div>
  )
  if (role === 'legal_reviewer') return (
    <div className="w-14 h-14 rounded-2xl bg-amber-100 flex items-center justify-center flex-shrink-0">
      <svg className="w-7 h-7 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z" />
        <path d="M2 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z" />
        <line x1="7" y1="21" x2="17" y2="21" />
        <line x1="12" y1="3" x2="12" y2="21" />
        <line x1="3" y1="6" x2="21" y2="6" />
      </svg>
    </div>
  )
  return (
    <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center flex-shrink-0">
      <svg className="w-7 h-7 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 00-3-3.87" />
        <path d="M16 3.13a4 4 0 010 7.75" />
      </svg>
    </div>
  )
}

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: number | string
  sub?: string
  accent?: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${accent ?? 'text-gray-900'}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

function SkeletonCard() {
  return <div className="h-24 rounded-xl bg-gray-100 animate-pulse" />
}

export default function DashboardPage() {
  const { username, role } = useAuth()
  const meta = ROLE_META[role ?? ''] ?? ROLE_META['investigator']
  const isAdmin = role === 'admin'

  const [cases, setCases] = useState<Case[]>([])
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        if (isAdmin) {
          setCases(await listAdminCases())
        } else {
          const [c, a] = await Promise.all([listCases(), listArtifacts()])
          setCases(c)
          setArtifacts(a)
        }
      } catch {
        // dashboard is best-effort — partial failures are silent
      } finally {
        setLoading(false)
      }
    })()
  }, [role])

  const ingested = artifacts.filter((a) => a.status === 'INGESTED').length
  const pending  = artifacts.filter((a) => a.status === 'PENDING').length
  const failed   = artifacts.filter((a) => a.status === 'INGESTION_FAILED').length
  const openCases   = cases.filter((c) => c.status === 'OPEN').length
  const closedCases = cases.filter((c) => c.status === 'CLOSED').length

  return (
    <Layout>
      <div className="max-w-5xl space-y-6">

        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-5 shadow-sm
                        flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <h1 className="text-xl font-bold text-gray-900">Welcome, {username}</h1>
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${meta.badge}`}>
                {meta.label}
              </span>
            </div>
            <p className="text-sm text-gray-500">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
              })}
            </p>
          </div>
          <RoleVisual role={role} />
        </div>

        {/* ── Stats ──────────────────────────────────────────────── */}
        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {[0, 1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
          </div>
        ) : isAdmin ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <StatCard label="Total Cases"  value={cases.length} />
            <StatCard label="Open"         value={openCases}   accent="text-emerald-600" />
            <StatCard label="Closed"       value={closedCases} accent="text-gray-400" />
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <StatCard label="Assigned Cases"  value={cases.length} />
            <StatCard label="Total Artifacts" value={artifacts.length} />
            <StatCard
              label="Ingested"
              value={ingested}
              sub="sealed in ledger"
              accent="text-emerald-600"
            />
            <StatCard
              label="Pending"
              value={pending}
              sub="awaiting ingestion"
              accent="text-amber-500"
            />
            <StatCard
              label="Failed"
              value={failed}
              sub="ingestion failed"
              accent={failed > 0 ? 'text-red-500' : 'text-gray-400'}
            />
          </div>
        )}

        {/* ── Main ───────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Cases list */}
          <div className="lg:col-span-2 rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {isAdmin ? 'All Cases' : 'Your Cases'}
              </span>
              {loading && (
                <span className="text-xs text-gray-400 animate-pulse">Loading…</span>
              )}
            </div>

            {!loading && cases.length === 0 ? (
              <div className="px-5 py-10 text-center text-sm text-gray-400">
                No cases found.
              </div>
            ) : (
              <ol className="divide-y divide-gray-100">
                {cases.slice(0, 8).map((c) => (
                  <li
                    key={c.id}
                    className="flex items-center justify-between px-5 py-3.5
                               hover:bg-slate-50 transition-colors gap-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-indigo-600 font-semibold flex-shrink-0">
                          {c.case_number}
                        </span>
                        <span className="text-sm text-gray-800 truncate">{c.title}</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {new Date(c.created_at).toLocaleDateString('en-US', {
                          month: 'short', day: 'numeric', year: 'numeric',
                        })}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <span
                        className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full ${
                          c.status === 'OPEN'
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {c.status}
                      </span>
                      {!isAdmin && (
                        <Link
                          to={`/cases/${c.case_number}`}
                          className="text-xs text-indigo-600 hover:text-indigo-500 hover:underline whitespace-nowrap"
                        >
                          View →
                        </Link>
                      )}
                    </div>
                  </li>
                ))}
                {cases.length > 8 && (
                  <li className="px-5 py-3 text-xs text-center text-gray-400">
                    +{cases.length - 8} more
                  </li>
                )}
              </ol>
            )}
          </div>

          {/* Quick actions */}
          <div className="space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-1">
              Quick Actions
            </p>

            {isAdmin && (
              <Link
                to="/admin/users"
                className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4
                           shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
              >
                <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-slate-600" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">Admin Panel</p>
                  <p className="text-xs text-gray-400">Manage users, cases &amp; assignments</p>
                </div>
              </Link>
            )}

            {(role === 'investigator' || role === 'forensic_analyst') && (
              <Link
                to="/artifacts/upload"
                className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4
                           shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
              >
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-indigo-600" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">Upload Evidence</p>
                  <p className="text-xs text-gray-400">Hash, sign, and seal a new artifact</p>
                </div>
              </Link>
            )}

            {!isAdmin && (
              <Link
                to="/artifacts"
                className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4
                           shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
              >
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-indigo-600" viewBox="0 0 24 24" fill="none"
                       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">Browse Evidence</p>
                  <p className="text-xs text-gray-400">View and filter all accessible artifacts</p>
                </div>
              </Link>
            )}

            <div className={`rounded-xl border p-4 ${TIP_COLORS[role ?? 'investigator']}`}>
              <p className="text-xs font-semibold mb-1">Tip</p>
              <p className="text-xs leading-relaxed">{meta.tip}</p>
            </div>
          </div>

        </div>
      </div>
    </Layout>
  )
}
