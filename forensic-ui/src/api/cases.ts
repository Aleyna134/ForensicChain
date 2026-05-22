import client from './client'

export interface Case {
  id: string
  case_number: string
  title: string
  description: string | null
  status: string
  created_at: string
  created_by: string
}

export interface CaseAssignment {
  id: string
  case_id: string
  username: string
  role_in_case: string
  assigned_at: string
  assigned_by: string
  is_active: boolean
}

export async function listCases(): Promise<Case[]> {
  const res = await client.get<Case[]>('/cases')
  return res.data
}

export async function listAdminCases(): Promise<Case[]> {
  const res = await client.get<Case[]>('/admin/cases')
  return res.data
}

export async function createCase(body: {
  case_number: string
  title: string
  description?: string
}): Promise<Case> {
  const res = await client.post<Case>('/admin/cases', body)
  return res.data
}

export async function updateCaseStatus(caseId: string, status: 'OPEN' | 'CLOSED'): Promise<Case> {
  const res = await client.patch<Case>(`/admin/cases/${caseId}`, { status })
  return res.data
}

export async function listAssignments(caseId: string): Promise<CaseAssignment[]> {
  const res = await client.get<CaseAssignment[]>(`/admin/cases/${caseId}/assignments`)
  return res.data
}

export async function createAssignment(
  caseId: string,
  body: { username: string; role_in_case: string },
): Promise<CaseAssignment> {
  const res = await client.post<CaseAssignment>(`/admin/cases/${caseId}/assignments`, body)
  return res.data
}

export async function deleteAssignment(caseId: string, assignmentId: string): Promise<void> {
  await client.delete(`/admin/cases/${caseId}/assignments/${assignmentId}`)
}
