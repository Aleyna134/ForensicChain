import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  downloadReport,
  generateReport,
  listReportsByArtifact,
  verifyReport,
  type Report,
  type ReportVerification,
} from '../api/reports'
import Layout from '../components/Layout'

export default function ReportPage() {
  const { artifactId } = useParams<{ artifactId: string }>()

  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [verifyingId, setVerifyingId] = useState<string | null>(null)
  const [verifications, setVerifications] = useState<Record<string, ReportVerification>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!artifactId) return
    listReportsByArtifact(artifactId)
      .then(setReports)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load reports'),
      )
      .finally(() => setLoading(false))
  }, [artifactId])

  async function handleGenerate() {
    if (!artifactId) return
    setGenerating(true)
    setError(null)
    try {
      const r = await generateReport(artifactId)
      setReports((prev) => [r, ...prev])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Report generation failed')
    } finally {
      setGenerating(false)
    }
  }

  async function handleDownload(reportId: string) {
    setDownloadingId(reportId)
    try {
      await downloadReport(reportId)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloadingId(null)
    }
  }

  async function handleVerify(reportId: string) {
    setVerifyingId(reportId)
    try {
      const v = await verifyReport(reportId)
      setVerifications((prev) => ({ ...prev, [reportId]: v }))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setVerifyingId(null)
    }
  }

  return (
    <Layout>
      <div className="max-w-5xl space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Link
                to={`/artifacts/${artifactId}`}
                className="text-slate-400 hover:text-slate-600 transition-colors flex-shrink-0"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">Forensic Reports</h1>
            </div>
            <p className="text-xs text-gray-400 font-mono mt-0.5 break-all pl-7">{artifactId}</p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex-shrink-0 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white
                       hover:bg-indigo-500 disabled:opacity-50 transition-colors"
          >
            {generating ? 'Generating…' : 'Generate new report'}
          </button>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-gray-100 animate-pulse" />
            ))}
          </div>
        ) : reports.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center">
            <p className="text-sm text-gray-500">No reports generated yet for this artifact.</p>
          </div>
        ) : (
          <section className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <div className="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Reports
              </span>
              <span className="text-xs text-gray-400">({reports.length})</span>
            </div>
            <ol className="divide-y divide-gray-100">
              {reports.map((r, idx) => {
                const v = verifications[r.report_id]
                return (
                  <li key={r.report_id} className="px-5 py-3.5 space-y-2">
                    <div className="flex items-center gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          {idx === 0 && (
                            <span className="text-[10px] font-semibold uppercase tracking-wider
                                             bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded">
                              Latest
                            </span>
                          )}
                          <span className="text-sm text-gray-700 font-mono truncate">
                            {r.report_id}
                          </span>
                        </div>
                        <p className="text-xs text-gray-400">
                          {new Date(r.generated_at).toLocaleString()} · {r.generated_by} · {r.format}
                        </p>
                      </div>
                      <div className="flex-shrink-0 flex items-center gap-2">
                        <button
                          onClick={() => handleVerify(r.report_id)}
                          disabled={verifyingId === r.report_id}
                          className="flex items-center gap-1.5 rounded-md border border-slate-200
                                     px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50
                                     disabled:opacity-50 transition-colors"
                        >
                          {verifyingId === r.report_id ? 'Verifying…' : 'Verify'}
                        </button>
                        <button
                          onClick={() => handleDownload(r.report_id)}
                          disabled={downloadingId === r.report_id}
                          className="flex items-center gap-1.5 rounded-md border border-slate-200
                                     px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50
                                     disabled:opacity-50 transition-colors"
                        >
                          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"
                               stroke="currentColor" strokeWidth="2"
                               strokeLinecap="round" strokeLinejoin="round">
                            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                            <polyline points="7 10 12 15 17 10" />
                            <line x1="12" y1="15" x2="12" y2="3" />
                          </svg>
                          {downloadingId === r.report_id ? 'Downloading…' : 'Download PDF'}
                        </button>
                      </div>
                    </div>

                    {v && (
                      <div className={`rounded-lg px-4 py-3 text-sm ${
                        v.report_valid
                          ? 'bg-emerald-50 border border-emerald-100'
                          : 'bg-red-50 border border-red-100'
                      }`}>
                        <p className={`font-semibold mb-2 ${v.report_valid ? 'text-emerald-700' : 'text-red-700'}`}>
                          {v.report_valid ? 'Report VALID ✓' : 'Report TAMPERED ✗'}
                        </p>
                        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
                          {(
                            [
                              ['Stored hash',  v.stored_hash],
                              ['Current hash', v.current_hash],
                              ['Verified at',  new Date(v.verified_at).toLocaleString()],
                            ] as [string, string][]
                          ).map(([label, value]) => (
                            <div key={label} className={label === 'Verified at' ? 'col-span-2' : ''}>
                              <dt className="text-gray-400">{label}</dt>
                              <dd className="font-mono break-all text-gray-700">{value}</dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}

                    <details className="text-xs">
                      <summary className="cursor-pointer text-gray-400 hover:text-gray-600 select-none">
                        Raw JSON
                      </summary>
                      <pre className="mt-2 overflow-auto whitespace-pre-wrap break-all text-gray-600 bg-gray-50 rounded-md p-3">
                        {JSON.stringify(v ? { report: r, verification: v } : r, null, 2)}
                      </pre>
                    </details>
                  </li>
                )
              })}
            </ol>
          </section>
        )}
      </div>
    </Layout>
  )
}
