import axios from 'axios'
import { clearToken, setToken } from '../hooks/useAuth'
import client from './client'

interface LoginResponse {
  access_token: string
  token_type: string
}

export async function login(username: string, password: string): Promise<void> {
  const response = await client.post<LoginResponse>('/auth/login', { username, password })
  setToken(response.data.access_token)
}

export function logout(): void {
  clearToken()
  window.location.href = '/login'
}

export { axios }
