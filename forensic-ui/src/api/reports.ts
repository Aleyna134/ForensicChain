import client from './client'

export interface Report {
  report_id: string
  artifact_id: string
  case_id: string | null
  report_hash: string
  format: string
  generated_at: string
  generated_by: string
  storage_path: string | null
}

export interface ReportVerification {
  report_id: string
  report_valid: boolean
  stored_hash: string
  current_hash: string
  verified_at: string
}

export async function listReportsByArtifact(artifactId: string): Promise<Report[]> {
  const res = await client.get<Report[]>(`/reports/by-artifact/${artifactId}`)
  return res.data
}

export async function generateReport(artifactId: string): Promise<Report> {
  const res = await client.post<Report>(`/reports/${artifactId}`)
  return res.data
}

export async function getReport(reportId: string): Promise<Report> {
  const res = await client.get<Report>(`/reports/${reportId}`)
  return res.data
}

export async function verifyReport(reportId: string): Promise<ReportVerification> {
  const res = await client.post<ReportVerification>(`/reports/${reportId}/verify`)
  return res.data
}

export async function downloadReport(reportId: string): Promise<void> {
  const res = await client.get(`/reports/${reportId}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `report-${reportId}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
