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

export function downloadReportUrl(reportId: string): string {
  return `/api/reports/${reportId}/download`
}
