import client from './client'

export interface LedgerRecord {
  record_id: string
  artifact_id: string
  case_id: string
  record_type: string
  hash_algorithm: string | null
  hash_value: string | null
  payload_hash: string
  previous_record_hash: string | null
  record_hash: string
  created_at: string
}

export interface LedgerValidation {
  case_id: string
  chain_valid: boolean
  checked_records: number
  error_message: string
}

export async function getLedgerRecords(caseId: string): Promise<LedgerRecord[]> {
  const res = await client.get<LedgerRecord[]>(`/ledger/records/${caseId}`)
  return res.data
}

export async function validateLedgerChain(caseId: string): Promise<LedgerValidation> {
  const res = await client.get<LedgerValidation>(`/ledger/validate/${caseId}`)
  return res.data
}
