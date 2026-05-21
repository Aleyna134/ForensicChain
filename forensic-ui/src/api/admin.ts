import client from './client'

export interface AdminUser {
  id: string
  username: string
  role: string
  is_active: boolean
  created_at: string
}

export interface CreateUserBody {
  username: string
  password: string
  role: string
}

export async function getUsers(): Promise<AdminUser[]> {
  const response = await client.get<AdminUser[]>('/admin/users')
  return response.data
}

export async function createUser(body: CreateUserBody): Promise<AdminUser> {
  const response = await client.post<AdminUser>('/admin/users', body)
  return response.data
}

export async function deleteUser(id: string): Promise<void> {
  await client.delete(`/admin/users/${id}`)
}
