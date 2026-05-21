import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listArtifacts, type Artifact } from '../api/evidence'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { getRole } from '../hooks/useAuth'

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

function SkeletonRow() {
  return (
    <tr>
      {['w-28', 'w-40', 'w-24', 'w-16', 'w-20', 'w-24', 'w-16'].map((w, i) => (
        <td key={i} className="px-4 py-3">
          <div className={`h-4 bg-slate-100 rounded animate-pulse ${w}`} />
        </td>
      ))}
    </tr>
  )
}

export default function ArtifactListPage() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [query, setQuery]         = useState('')

  const role = getRole()

  useEffect(() => {
    listArtifacts()
      .then(setArtifacts)
      .catch(() => setError('Failed to load artifacts. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!query.trim()) return artifacts
    const q = query.trim().toLowerCase()
    return artifacts.filter(
      (a) =>
        a.case_id.toLowerCase().includes(q) ||
        a.file_name.toLowerCase().includes(q) ||
        a.artifact_type.toLowerCase().includes(q),
    )
  }, [artifacts, query])

  return (
    <Layout>
      <div className="h-full flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <h1 className="text-xl font-semibold text-slate-800">My Artifacts</h1>
            {!loading && !error && (
              <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded-full
                               text-xs font-medium bg-slate-100 text-slate-600">
                {artifacts.length} {artifacts.length === 1 ? 'artifact' : 'artifacts'}
              </span>
            )}
          </div>

          {(role === 'investigator' || role === 'forensic_analyst') && (
            <Link
              to="/artifacts/upload"
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800
                         text-xs font-semibold text-white hover:bg-slate-700 transition-colors"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Upload Evidence
            </Link>
          )}
        </div>

        {/* Search */}
        <div className="mb-4">
          <div className="relative w-72">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400"
                 viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              placeholder="Filter by case, filename, or type…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 bg-white
                         text-sm text-slate-700 placeholder-slate-400
                         focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                         transition-all"
            />
          </div>
        </div>

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

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden w-full">
          <table className="w-full divide-y divide-slate-200">
            <thead>
              <tr className="bg-slate-50">
                {['Case ID', 'Filename', 'Type', 'Size', 'Status', 'Uploaded', ''].map((col) => (
                  <th key={col}
                      className="px-4 py-3 text-left text-xs font-semibold text-slate-500
                                 uppercase tracking-wider whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading
                ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
                : filtered.length === 0
                  ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-12 text-center">
                        <div className="flex flex-col items-center gap-2 text-slate-400">
                          <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                               strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                          <p className="text-sm">
                            {query ? 'No artifacts match your filter.' : 'No artifacts yet.'}
                          </p>
                          {!query && role === 'investigator' && (
                            <Link to="/artifacts/upload"
                                  className="text-xs text-indigo-600 hover:underline mt-1">
                              Upload your first artifact →
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                  : filtered.map((a) => (
                    <tr key={a.artifact_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono text-slate-700 whitespace-nowrap">
                        {a.case_id}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700 max-w-[180px] truncate"
                          title={a.file_name}>
                        {a.file_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">
                        {a.artifact_type}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">
                        {formatSize(a.file_size)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={a.status} />
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">
                        {formatDate(a.uploaded_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/artifacts/${a.artifact_id}`}
                          className="text-xs font-medium text-indigo-600 hover:text-indigo-500
                                     hover:underline whitespace-nowrap"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>

      </div>
    </Layout>
  )
}
