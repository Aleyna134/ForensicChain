import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { downloadArtifact, getArtifact, verifyArtifact, type Artifact, type VerificationResult } from '../api/evidence'
import { getTimeline, type Timeline } from '../api/custody'
import FilePickerInput from '../components/FilePickerInput'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { getRole } from '../hooks/useAuth'

export default function ArtifactDetailPage() {
  const { id } = useParams<{ id: string }>()

  const [artifact, setArtifact] = useState<Artifact | null>(null)
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const [fetchError, setFetchError] = useState<string | null>(null)

  const [verifyResult, setVerifyResult] = useState<VerificationResult | null>(null)
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const [verifying, setVerifying] = useState(false)

  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const fileRef = useRef<HTMLInputElement>(null)
  const role = getRole()

  useEffect(() => {
    if (!id) return

    getArtifact(id)
      .then(setArtifact)
      .catch((err: unknown) =>
        setFetchError(err instanceof Error ? err.message : 'Failed to load artifact'),
      )

    // Custody timeline is only accessible to forensic_analyst and legal_reviewer.
    // For investigator role this returns 403 — load it independently so a rejection
    // here doesn't block the artifact detail view.
    getTimeline(id)
      .then(setTimeline)
      .catch(() => { /* role lacks custody access — section simply stays hidden */ })
  }, [id])

  async function handleDownload() {
    if (!artifact) return
    setDownloading(true)
    setDownloadError(null)
    try {
      await downloadArtifact(artifact.artifact_id, artifact.file_name)
    } catch {
      setDownloadError('Download failed. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file || !id) return
    setVerifying(true)
    setVerifyError(null)
    setVerifyResult(null)
    try {
      const result = await verifyArtifact(id, file)
      setVerifyResult(result)
    } catch (err: unknown) {
      setVerifyError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setVerifying(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-5xl space-y-6">
        <div className="flex items-center gap-2">
          <Link to="/artifacts" className="text-slate-400 hover:text-slate-600 transition-colors">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Artifact Detail</h1>
        </div>

        {fetchError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {fetchError}
          </div>
        )}

        {/* ── Metadata ─────────────────────────────────────────────── */}
        {artifact && (
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-800">Metadata</h2>
              <StatusBadge status={artifact.status} />
            </div>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm mb-4">
              {(
                [
                  ['Case ID', artifact.case_id],
                  ['File', artifact.file_name],
                  ['Type', artifact.artifact_type],
                  ['Size', `${artifact.file_size} B`],
                  ['Hash algo', artifact.hash_algorithm],
                  ['Uploaded by', artifact.uploaded_by],
                  ['Uploaded', artifact.uploaded_at?.slice(0, 19).replace('T', ' ')],
                ] as [string, string | null | undefined][]
              ).map(([label, value]) => (
                <div key={label}>
                  <dt className="text-gray-400">{label}</dt>
                  <dd className={`text-gray-700 font-mono ${label === 'File' ? 'break-all' : 'truncate'}`}>
                    {value ?? '—'}
                  </dd>
                </div>
              ))}
            </dl>
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-400 hover:text-gray-600">
                Raw JSON
              </summary>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap break-all text-gray-600 bg-gray-50 rounded-md p-3">
                {JSON.stringify(artifact, null, 2)}
              </pre>
            </details>
            <div className="mt-4 flex items-center gap-4 flex-wrap">
              {role === 'legal_reviewer' && (
                <Link
                  to={`/reports/${id}`}
                  className="text-sm text-indigo-600 hover:underline"
                >
                  Generate / view report →
                </Link>
              )}

              {role === 'forensic_analyst' && (
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  className="flex items-center gap-1.5 rounded-md border border-slate-200 px-3 py-1.5
                             text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  {downloading ? 'Downloading…' : 'Download file'}
                </button>
              )}
            </div>

            {downloadError && (
              <p className="mt-2 text-xs text-red-600">{downloadError}</p>
            )}
          </section>
        )}

        {/* ── Verify integrity ─────────────────────────────────────── */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Verify Integrity</h2>

          <form onSubmit={handleVerify} className="flex items-center gap-3 flex-wrap mb-3">
            <FilePickerInput inputRef={fileRef} />
            <button
              type="submit"
              disabled={verifying}
              className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {verifying ? 'Verifying…' : 'Verify file'}
            </button>
          </form>

          {verifyError && (
            <p className="mt-2 text-xs text-red-600">{verifyError}</p>
          )}

          {verifyResult && (
            <div className="mt-4 rounded-lg border border-gray-200 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-100">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Verification Result
                </span>
                <StatusBadge status={verifyResult.verification_result} />
              </div>
              <dl className="divide-y divide-gray-100">
                {(
                  [
                    ['Original Hash',      verifyResult.original_hash],
                    ['Current Hash',       verifyResult.current_hash],
                    ['Signature Valid',    verifyResult.signature_valid    ? 'Yes' : 'No'],
                    ['Ledger Chain Valid', verifyResult.ledger_chain_valid ? 'Yes' : 'No'],
                    ['Verified At',        new Date(verifyResult.verified_at).toLocaleString()],
                  ] as [string, string][]
                ).map(([label, value]) => (
                  <div key={label} className="flex items-baseline px-4 py-2.5 gap-4">
                    <dt className="w-40 flex-shrink-0 text-xs font-medium text-gray-400 uppercase tracking-wider">
                      {label}
                    </dt>
                    <dd className="text-sm text-gray-700 font-mono break-all">{value}</dd>
                  </div>
                ))}
              </dl>
              <details className="border-t border-gray-100">
                <summary className="px-4 py-2.5 cursor-pointer text-xs text-gray-400 hover:text-gray-600 select-none">
                  Raw JSON
                </summary>
                <pre className="px-4 pb-3 text-xs text-gray-600 bg-gray-50 overflow-auto whitespace-pre-wrap break-all">
                  {JSON.stringify(verifyResult, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </section>

        {/* ── Custody timeline ─────────────────────────────────────── */}
        {timeline && (
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-800">
                Custody Timeline
                <span className="ml-2 text-sm font-normal text-gray-400">
                  {timeline.total_events} event{timeline.total_events !== 1 ? 's' : ''}
                </span>
              </h2>
              <span
                className={`text-xs font-semibold ${
                  timeline.chain_valid ? 'text-emerald-600' : 'text-red-600'
                }`}
              >
                Chain {timeline.chain_valid ? 'valid ✓' : 'BROKEN ✗'}
              </span>
            </div>

            <ol className="relative border-l border-gray-200 pl-5 space-y-4">
              {timeline.events.map((ev) => (
                <li key={ev.event_id} className="relative">
                  <span className="absolute -left-[21px] top-1.5 h-3 w-3 rounded-full bg-indigo-400 ring-2 ring-white" />
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm font-medium text-gray-800">{ev.event_type}</span>
                    <span className="flex-shrink-0 text-xs text-gray-400">
                      {new Date(ev.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    {ev.actor_id} · {ev.actor_role}
                  </p>
                  {ev.reason && (
                    <p className="text-xs text-gray-400 italic">{ev.reason}</p>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </Layout>
  )
}
