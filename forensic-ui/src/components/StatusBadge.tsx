type StatusKey =
  | 'INGESTED'
  | 'PENDING'
  | 'INGESTION_FAILED'
  | 'VALID'
  | 'TAMPERED'
  | 'INVALID_SIGNATURE'
  | 'LEDGER_CORRUPTED'

const PALETTE: Record<StatusKey, string> = {
  INGESTED:          'bg-emerald-100 text-emerald-800',
  PENDING:           'bg-amber-100   text-amber-800',
  INGESTION_FAILED:  'bg-red-100     text-red-800',
  VALID:             'bg-emerald-100 text-emerald-800',
  TAMPERED:          'bg-red-100     text-red-800',
  INVALID_SIGNATURE: 'bg-orange-100  text-orange-800',
  LEDGER_CORRUPTED:  'bg-red-200     text-red-900',
}

interface Props {
  status: string
}

export default function StatusBadge({ status }: Props) {
  const cls = PALETTE[status as StatusKey] ?? 'bg-gray-100 text-gray-700'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}
    >
      {status}
    </span>
  )
}
