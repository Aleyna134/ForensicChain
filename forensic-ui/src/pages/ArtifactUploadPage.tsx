import { useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadArtifact, type Artifact } from '../api/evidence'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'

// ── Constants ─────────────────────────────────────────────────────────────────

const ARTIFACT_TYPES = [
  'MobileExtraction',
  'DiskImage',
  'MemoryDump',
  'NetworkCapture',
  'LogFile',
  'Other',
] as const

const CASE_ID_RE = /^CASE-\d{4}-\d{3}$/

interface TypeInfo {
  type: string
  label: string
  description: string
  examples: string[]
  icon: string
}

const TYPE_INFO: TypeInfo[] = [
  {
    type: 'MobileExtraction',
    label: 'Mobile Extraction',
    icon: 'M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z',
    description: 'Data extracted from mobile devices using forensic tools.',
    examples: ['iOS/Android logical or physical dumps', 'WhatsApp, Signal, iMessage exports', 'Call logs, contacts, location history'],
  },
  {
    type: 'DiskImage',
    label: 'Disk Image',
    icon: 'M5 3a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2H5zm0 0',
    description: 'Bit-for-bit forensic copy of a storage device.',
    examples: ['.dd / .E01 / .AFF images', 'Hard drives, SSDs, USB drives', 'RAID and partition captures'],
  },
  {
    type: 'MemoryDump',
    label: 'Memory Dump',
    icon: 'M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18',
    description: "Point-in-time snapshot of a system's volatile RAM.",
    examples: ['Volatility captures (.raw, .mem)', 'Windows crash dumps (.dmp)', 'Hibernation files (hiberfil.sys)'],
  },
  {
    type: 'NetworkCapture',
    label: 'Network Capture',
    icon: 'M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0',
    description: 'Recorded network packets or traffic metadata.',
    examples: ['.pcap / .pcapng (Wireshark)', 'Firewall and proxy logs', 'NetFlow / IPFIX records'],
  },
  {
    type: 'LogFile',
    label: 'Log File',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    description: 'System, application, or security event logs.',
    examples: ['Windows Event Logs (.evtx)', 'Syslog, auth.log, kern.log', 'Web server access & error logs'],
  },
  {
    type: 'Other',
    label: 'Other',
    icon: 'M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z',
    description: 'Any digital evidence not covered by the categories above.',
    examples: ['Screenshots, documents, emails', 'Database exports, registry hives', 'Browser history, cloud backups'],
  },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}


// ── Type guide panel ──────────────────────────────────────────────────────────

function TypeGuide({ selected }: { selected: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
        <h2 className="text-sm font-semibold text-slate-700">Artifact Type Guide</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Select a type that best matches your evidence.
        </p>
      </div>
      <ul className="divide-y divide-slate-100">
        {TYPE_INFO.map((info) => {
          const isActive = info.type === selected
          return (
            <li key={info.type} className="flex items-stretch">
              {/* Left accent bar — reliable alternative to border-l-{color} */}
              <span className={`w-[3px] flex-shrink-0 transition-colors ${
                isActive ? 'bg-indigo-500' : 'bg-transparent'
              }`} />
              <div className={`flex-1 px-5 py-4 transition-colors ${isActive ? 'bg-indigo-50' : ''}`}>
              <div className="flex items-start gap-3">
                <svg
                  className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isActive ? 'text-indigo-500' : 'text-slate-400'}`}
                  viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                >
                  <path d={info.icon} />
                </svg>
                <div className="min-w-0">
                  <p className={`text-sm font-medium ${isActive ? 'text-indigo-700' : 'text-slate-700'}`}>
                    {info.label}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                    {info.description}
                  </p>
                  <ul className="mt-1.5 space-y-0.5">
                    {info.examples.map((ex) => (
                      <li key={ex} className="flex items-center gap-1.5 text-[11px] text-slate-400">
                        <span className={`w-1 h-1 rounded-full flex-shrink-0 ${isActive ? 'bg-indigo-400' : 'bg-slate-300'}`} />
                        {ex}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

// ── Success card ──────────────────────────────────────────────────────────────

interface SuccessCardProps {
  result: Artifact
  onViewArtifact: () => void
  onUploadAnother: () => void
}

function SuccessCard({ result, onViewArtifact, onUploadAnother }: SuccessCardProps) {
  const fields: { label: string; value: string }[] = [
    { label: 'Artifact ID',    value: result.artifact_id },
    { label: 'Case ID',        value: result.case_id },
    { label: 'File',           value: `${result.file_name}  (${formatFileSize(result.file_size)})` },
    ...(result.uploaded_at ? [
      { label: 'Ingested at',  value: formatDateTime(result.uploaded_at) },
    ] : []),
  ]

  return (
    <div className="max-w-xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-9 h-9 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-emerald-600" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-800">Evidence ingested successfully</h1>
          <p className="text-sm text-slate-500">The artifact has been hashed, signed, and recorded on the ledger.</p>
        </div>
      </div>

      {/* Detail card */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden mb-5">
        <div className="flex items-center justify-between px-5 py-3 bg-slate-50 border-b border-slate-100">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Artifact record
          </span>
          <StatusBadge status={result.status} />
        </div>
        <dl className="divide-y divide-slate-100">
          {fields.map(({ label, value }) => (
            <div key={label} className="flex items-baseline px-5 py-3 gap-4">
              <dt className="w-36 flex-shrink-0 text-xs font-medium text-slate-400 uppercase tracking-wider">
                {label}
              </dt>
              <dd className="text-sm text-slate-800 font-mono break-all">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={onViewArtifact}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2.5
                     text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
        >
          View artifact
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
        <button
          onClick={onUploadAnother}
          className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-medium
                     text-slate-600 hover:bg-slate-50 transition-colors"
        >
          Upload another
        </button>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ArtifactUploadPage() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)

  const [caseId,       setCaseId]       = useState('')
  const [title,        setTitle]        = useState('')
  const [artifactType, setArtifactType] = useState<string>(ARTIFACT_TYPES[0])
  const [description,  setDescription]  = useState('')
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState<string | null>(null)
  const [result,       setResult]       = useState<Artifact | null>(null)

  function resetForm() {
    setCaseId('')
    setTitle('')
    setArtifactType(ARTIFACT_TYPES[0])
    setDescription('')
    setError(null)
    setResult(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()

    if (!CASE_ID_RE.test(caseId)) {
      setError('Case ID must match the format CASE-YYYY-NNN (e.g. CASE-2026-001).')
      return
    }

    const file = fileRef.current?.files?.[0]
    if (!file) {
      setError('Please select a file.')
      return
    }

    const fd = new FormData()
    fd.append('file', file)
    fd.append('case_id', caseId)
    fd.append('title', title)
    fd.append('artifact_type', artifactType)
    if (description) fd.append('description', description)

    setLoading(true)
    setError(null)
    try {
      setResult(await uploadArtifact(fd))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (result) {
    return (
      <Layout>
        <SuccessCard
          result={result}
          onViewArtifact={() => navigate(`/artifacts/${result.artifact_id}`)}
          onUploadAnother={resetForm}
        />
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="flex gap-8 items-start">

        {/* ── Left: form ──────────────────────────────────────────────── */}
        <div className="w-full max-w-[480px] flex-shrink-0">
          <h1 className="text-xl font-bold text-slate-800 mb-5">Upload Evidence</h1>

          <form
            onSubmit={handleSubmit}
            className="rounded-xl border border-slate-200 bg-white p-6 space-y-4"
          >
            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200
                              bg-red-50 px-3 py-2.5 text-sm text-red-700">
                <svg className="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                </svg>
                {error}
              </div>
            )}

            {/* File */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                File <span className="text-red-500">*</span>
              </label>
              <input ref={fileRef} type="file" required
                     className="text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-3
                                file:rounded-md file:border-0 file:text-sm file:font-medium
                                file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200" />
            </div>

            {/* Case ID */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Case ID <span className="text-red-500">*</span>
              </label>
              <input
                required
                placeholder="CASE-2026-001"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value.toUpperCase())}
                pattern="CASE-\d{4}-\d{3}"
                title="Format: CASE-YYYY-NNN (e.g. CASE-2026-001)"
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm
                           font-mono outline-none focus:ring-2 focus:ring-indigo-500/20
                           focus:border-indigo-400 transition-all"
              />
              <p className="mt-1 text-[11px] text-slate-400">Format: CASE-YYYY-NNN — e.g. CASE-2026-001</p>
            </div>

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Title <span className="text-red-500">*</span>
              </label>
              <input
                required
                placeholder="Phone extraction from suspect device"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm
                           outline-none focus:ring-2 focus:ring-indigo-500/20
                           focus:border-indigo-400 transition-all"
              />
            </div>

            {/* Artifact Type */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Artifact Type
              </label>
              <select
                value={artifactType}
                onChange={(e) => setArtifactType(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm
                           outline-none focus:ring-2 focus:ring-indigo-500/20
                           focus:border-indigo-400 transition-all"
              >
                {ARTIFACT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_INFO.find((i) => i.type === t)?.label ?? t}
                  </option>
                ))}
              </select>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Description
                <span className="ml-1 text-xs font-normal text-slate-400">(optional)</span>
              </label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Briefly describe the source, collection method, or relevant context…"
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm
                           outline-none focus:ring-2 focus:ring-indigo-500/20
                           focus:border-indigo-400 transition-all resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold
                         text-white hover:bg-indigo-500 disabled:opacity-50
                         disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Uploading…' : 'Upload artifact'}
            </button>
          </form>
        </div>

        {/* ── Right: type guide ────────────────────────────────────────── */}
        <div className="flex-1 min-w-[260px]">
          <TypeGuide selected={artifactType} />
        </div>

      </div>
    </Layout>
  )
}
