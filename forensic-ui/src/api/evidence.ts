import client from './client'

export interface Artifact {
  artifact_id: string
  case_id: string
  file_name: string
  file_size: number
  artifact_type: string
  description: string | null
  hash_algorithm: string | null
  hash_value: string | null
  signature_value: string | null
  ledger_record_id: string | null
  status: 'PENDING' | 'INGESTED' | 'INGESTION_FAILED'
  uploaded_at: string | null
}

export interface VerificationResult {
  artifact_id: string
  verification_result: 'VALID' | 'TAMPERED' | 'INVALID_SIGNATURE' | 'LEDGER_CORRUPTED'
  original_hash: string
  current_hash: string
  signature_valid: boolean
  ledger_chain_valid: boolean
  verified_at: string
}

export async function getArtifact(id: string): Promise<Artifact> {
  const res = await client.get<Artifact>(`/evidence/${id}`)
  return res.data
}

export async function uploadArtifact(formData: FormData): Promise<Artifact> {
  const res = await client.post<Artifact>('/evidence', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function verifyArtifact(id: string, file: File): Promise<VerificationResult> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await client.post<VerificationResult>(`/evidence/${id}/verify`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function listArtifacts(caseId?: string): Promise<Artifact[]> {
  const params = caseId ? { case_id: caseId } : {}
  const res = await client.get<Artifact[]>('/evidence', { params })
  return res.data
}

export async function downloadArtifact(id: string, fileName: string): Promise<void> {
  const res = await client.get(`/evidence/${id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}
