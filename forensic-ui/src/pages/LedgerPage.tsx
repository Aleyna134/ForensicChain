import { useEffect, useState } from 'react'
import { listCases, type Case } from '../api/cases'
import { getLedgerRecords, validateLedgerChain, type LedgerRecord, type LedgerValidation } from '../api/ledger'
import Layout from '../components/Layout'

const RECORD_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  EVIDENCE_PROOF_CREATED:      { label: 'Proof',        color: 'bg-blue-100 text-blue-700' },
  VERIFICATION_RESULT_RECORDED: { label: 'Verification', color: 'bg-violet-100 text-violet-700' },
  REPORT_PROOF_CREATED:        { label: 'Report',       color: 'bg-amber-100 text-amber-700' },
}

function shortHash(hash: string | null | undefined, len = 12): string {
  if (!hash) return '—'
  return hash.slice(0, len) + '…'
}

function shortId(id: string, len = 8): string {
  return id.slice(0, len) + '…'
}

function RecordTypeBadge({ type }: { type: string }) {
  const meta = RECORD_TYPE_LABELS[type] ?? { label: type, color: 'bg-slate-100 text-slate-600' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${meta.color}`}>
      {meta.label}
    </span>
  )
}

export default function LedgerPage() {
  const [cases, setCases] = useState<Case[]>([])
  const [selectedCase, setSelectedCase] = useState<string>('')
  const [records, setRecords] = useState<LedgerRecord[]>([])
  const [validation, setValidation] = useState<LedgerValidation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listCases()
      .then((data) => {
        setCases(data)
        if (data.length > 0) setSelectedCase(data[0].case_number)
      })
      .catch(() => setError('Could not load cases.'))
  }, [])

  useEffect(() => {
    if (!selectedCase) return
    setLoading(true)
    setError(null)
    setRecords([])
    setValidation(null)

    Promise.all([getLedgerRecords(selectedCase), validateLedgerChain(selectedCase)])
      .then(([recs, val]) => {
        setRecords(recs)
        setValidation(val)
      })
      .catch(() => setError('Failed to load ledger data.'))
      .finally(() => setLoading(false))
  }, [selectedCase])

  const selectedCaseObj = cases.find((c) => c.case_number === selectedCase)

  return (
    <Layout>
      <div className="max-w-5xl space-y-6">

        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-800">Immutable Ledger</h1>
            <p className="text-sm text-slate-500 mt-0.5">Cryptographic chain of evidence integrity records</p>
          </div>

          {/* Case selector */}
          <select
            value={selectedCase}
            onChange={(e) => setSelectedCase(e.target.value)}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700
                       bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {cases.map((c) => (
              <option key={c.case_number} value={c.case_number}>
                {c.case_number} — {c.title}
              </option>
            ))}
          </select>
        </div>

        {/* ── Validation banner ───────────────────────────────────────── */}
        {validation && (
          <div className={`rounded-xl border px-5 py-4 flex items-start gap-3 ${
            validation.chain_valid
              ? 'border-emerald-200 bg-emerald-50'
              : 'border-red-200 bg-red-50'
          }`}>
            {validation.chain_valid ? (
              <svg className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            )}
            <div>
              <p className={`text-sm font-semibold ${validation.chain_valid ? 'text-emerald-800' : 'text-red-800'}`}>
                {validation.chain_valid
                  ? `Chain Intact — ${validation.checked_records} record${validation.checked_records !== 1 ? 's' : ''} verified`
                  : 'Chain Integrity Failure'}
              </p>
              {!validation.chain_valid && validation.error_message && (
                <p className="text-xs text-red-600 mt-0.5">{validation.error_message}</p>
              )}
              {selectedCaseObj && (
                <p className="text-xs text-slate-500 mt-0.5">{selectedCaseObj.case_number} — {selectedCaseObj.title}</p>
              )}
            </div>
          </div>
        )}

        {/* ── Loading / error states ──────────────────────────────────── */}
        {loading && (
          <div className="text-center py-12 text-slate-400 text-sm">Loading ledger records…</div>
        )}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>
        )}

        {/* ── Records table ───────────────────────────────────────────── */}
        {!loading && !error && records.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wide">
                  <th className="px-4 py-3 text-left w-8">#</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Artifact ID</th>
                  <th className="px-4 py-3 text-left">Record Hash</th>
                  <th className="px-4 py-3 text-left">Prev Hash</th>
                  <th className="px-4 py-3 text-left">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {records.map((rec, idx) => (
                  <tr key={rec.record_id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-slate-400 text-xs font-mono">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <RecordTypeBadge type={rec.record_type} />
                        {rec.previous_record_hash === null && (
                          <span className="text-xs text-slate-400 font-medium">genesis</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600" title={rec.artifact_id}>
                      {shortId(rec.artifact_id)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600" title={rec.record_hash}>
                      {shortHash(rec.record_hash)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400" title={rec.previous_record_hash ?? ''}>
                      {rec.previous_record_hash ? shortHash(rec.previous_record_hash) : <span className="italic">—</span>}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {new Date(rec.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !error && records.length === 0 && selectedCase && (
          <div className="text-center py-12 text-slate-400 text-sm">
            No ledger records found for {selectedCase}.
          </div>
        )}
      </div>
    </Layout>
  )
}
