import { jwtDecode } from 'jwt-decode'

const TOKEN_KEY = 'fc_token'

interface JwtPayload {
  sub: string
  username?: string
  role: string
  exp: number
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

function decodeToken(): JwtPayload | null {
  const token = getToken()
  if (!token) return null
  try {
    return jwtDecode<JwtPayload>(token)
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  const payload = decodeToken()
  if (!payload) return false
  return payload.exp * 1000 > Date.now()
}

export function getRole(): string | null {
  return decodeToken()?.role ?? null
}

export function getUsername(): string | null {
  const p = decodeToken()
  if (!p) return null
  return p.username ?? p.sub
}

export function hasRole(roles: string[]): boolean {
  const role = getRole()
  if (!role) return false
  return roles.includes(role)
}

export function useAuth() {
  const payload = decodeToken()
  return {
    token: getToken(),
    username: payload?.username ?? payload?.sub ?? null,
    role: payload?.role ?? null,
    isAuthenticated: isAuthenticated(),
    hasRole,
    setToken,
    logout() {
      clearToken()
      window.location.href = '/login'
    },
  }
}
