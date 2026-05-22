import axios from 'axios'
import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { getRole, isAuthenticated } from '../hooks/useAuth'

function redirectForRole(_role: string | null): string {
  return '/'
}

// ── Network visualization ─────────────────────────────────────────────────────

interface NetNode { x: number; y: number; r: number; bright: boolean; delay: number }
type NetEdge = [number, number]

const NET_NODES: NetNode[] = [
  { x: 95,  y: 55,  r: 1.8, bright: false, delay: 0.0  },
  { x: 230, y: 35,  r: 2.5, bright: true,  delay: 0.9  },
  { x: 355, y: 80,  r: 2.0, bright: false, delay: 1.8  },
  { x: 480, y: 50,  r: 2.8, bright: true,  delay: 2.7  },
  { x: 605, y: 100, r: 1.8, bright: false, delay: 0.6  },
  { x: 710, y: 60,  r: 2.2, bright: true,  delay: 1.5  },
  { x: 55,  y: 175, r: 2.5, bright: false, delay: 0.3  },
  { x: 170, y: 200, r: 4.0, bright: true,  delay: 1.2  },
  { x: 310, y: 160, r: 3.0, bright: false, delay: 2.1  },
  { x: 440, y: 210, r: 5.0, bright: true,  delay: 0.0  },
  { x: 580, y: 175, r: 3.0, bright: false, delay: 1.9  },
  { x: 700, y: 220, r: 2.5, bright: true,  delay: 0.8  },
  { x: 110, y: 315, r: 3.0, bright: true,  delay: 1.4  },
  { x: 260, y: 295, r: 5.5, bright: true,  delay: 0.5  },
  { x: 400, y: 340, r: 3.5, bright: false, delay: 2.3  },
  { x: 535, y: 305, r: 6.0, bright: true,  delay: 1.1  },
  { x: 680, y: 355, r: 2.5, bright: false, delay: 2.6  },
  { x: 50,  y: 450, r: 2.5, bright: false, delay: 0.7  },
  { x: 190, y: 430, r: 4.0, bright: true,  delay: 1.6  },
  { x: 340, y: 470, r: 3.0, bright: false, delay: 0.2  },
  { x: 475, y: 440, r: 4.5, bright: true,  delay: 2.0  },
  { x: 620, y: 475, r: 2.5, bright: false, delay: 1.3  },
  { x: 720, y: 430, r: 3.0, bright: true,  delay: 0.4  },
  { x: 120, y: 570, r: 3.5, bright: true,  delay: 2.2  },
  { x: 275, y: 555, r: 2.5, bright: false, delay: 0.8  },
  { x: 420, y: 590, r: 5.0, bright: true,  delay: 1.7  },
  { x: 565, y: 560, r: 3.0, bright: false, delay: 0.1  },
  { x: 700, y: 600, r: 2.5, bright: true,  delay: 2.4  },
]

const NET_EDGES: NetEdge[] = [
  [0,1],[1,2],[2,3],[3,4],[4,5],
  [0,6],[1,6],[1,7],[2,7],[2,8],[3,8],[3,9],[4,9],[4,10],[5,10],[5,11],
  [6,7],[7,8],[8,9],[9,10],[10,11],
  [6,12],[7,12],[7,13],[8,13],[9,13],[9,14],[9,15],[10,15],[11,15],[11,16],
  [12,13],[13,14],[14,15],[15,16],
  [12,17],[13,17],[13,18],[14,18],[14,19],[15,19],[15,20],[16,20],[16,21],[16,22],
  [17,18],[18,19],[19,20],[20,21],[21,22],
  [17,23],[18,23],[18,24],[19,24],[19,25],[20,25],[21,25],[21,26],[22,26],[22,27],
  [23,24],[24,25],[25,26],[26,27],
  [9,15],[13,20],[15,25],
]

function NetworkBackground() {
  return (
    <svg viewBox="0 0 740 660" className="w-full h-full"
         preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <radialGradient id="nbg" cx="55%" cy="42%" r="60%">
          <stop offset="0%"   stopColor="#0a2a50" stopOpacity="0.85" />
          <stop offset="70%"  stopColor="#050e1e" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#030810" stopOpacity="1"    />
        </radialGradient>
        <filter id="nglow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="eglow" x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation="1.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <rect width="740" height="660" fill="url(#nbg)" />

      <g filter="url(#eglow)">
        {NET_EDGES.map(([a, b], i) => (
          <line key={i}
            x1={NET_NODES[a].x} y1={NET_NODES[a].y}
            x2={NET_NODES[b].x} y2={NET_NODES[b].y}
            stroke="#22d3ee" strokeWidth="0.5"
            className="n-edge"
            style={{ animationDelay: `${(i * 0.22) % 7}s` }}
          />
        ))}
      </g>

      <g filter="url(#nglow)">
        {NET_NODES.map((n, i) => (
          <circle key={i}
            cx={n.x} cy={n.y} r={n.r}
            fill={n.bright ? '#22d3ee' : '#60a5fa'}
            className="n-node"
            style={{ animationDelay: `${n.delay}s` }}
          />
        ))}
      </g>
    </svg>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [error,    setError]    = useState<string | null>(null)
  const [loading,  setLoading]  = useState(false)

  if (isAuthenticated()) {
    return <Navigate to={redirectForRole(getRole())} replace />
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(username, password)
      navigate(redirectForRole(getRole()), { replace: true })
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        setError('Invalid credentials. Please try again.')
      } else {
        setError('Unable to connect. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{`
        .n-node { animation: nPulse 4s ease-in-out infinite; }
        .n-edge { animation: nShimmer 5s ease-in-out infinite; }
        @keyframes nPulse   { 0%,100%{opacity:0.35} 50%{opacity:1}   }
        @keyframes nShimmer { 0%,100%{stroke-opacity:0.1} 50%{stroke-opacity:0.38} }
        .fc-input { outline: none; }
        .fc-input:focus {
          border-color: rgba(34,211,238,0.55) !important;
          box-shadow: 0 0 0 3px rgba(34,211,238,0.08);
        }
        @media (prefers-reduced-motion: reduce) {
          .n-node, .n-edge { animation: none !important; }
        }
      `}</style>

      <div className="flex flex-col h-screen overflow-hidden" style={{ background: '#060d1a' }}>

        {/* ── Main row ──────────────────────────────────────────────────── */}
        <div className="flex flex-1 min-h-0">

          {/* Left panel */}
          <div className="hidden md:block relative flex-1" style={{ background: '#04080f' }}>
            <div className="absolute inset-0">
              <NetworkBackground />
            </div>

            {/* Logo */}
            <div className="absolute top-8 left-8 z-10 flex items-center gap-2.5">
              <div className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
                   style={{ background: '#0b1e35', border: '1px solid rgba(34,211,238,0.3)' }}>
                <svg className="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="M9 12l2 2 4-4" />
                </svg>
              </div>
              <span className="text-white font-semibold text-sm tracking-wide">ForensicChain</span>
            </div>

            {/* Bottom copy */}
            <div className="absolute bottom-0 left-0 right-0 z-10 p-10 pb-12"
                 style={{ background: 'linear-gradient(to top, rgba(4,8,15,0.97) 40%, transparent)' }}>
              <h1 className="text-[46px] font-extrabold text-white leading-tight mb-4">
                Secure Digital Evidence<br />Management
              </h1>
              <p className="text-slate-400 text-[13px] leading-relaxed mb-6 max-w-[430px]">
                Immutable verification, forensic integrity, and end-to-end
                auditability for modern investigative units.
              </p>
              <div className="flex items-center gap-8">
                <span className="flex items-center gap-2 text-[11px] text-slate-400 tracking-[0.14em] uppercase">
                  <span className="w-2 h-2 rounded-full" style={{ background: '#4ade80' }} />
                  Network Secure
                </span>
                <span className="flex items-center gap-2 text-[11px] text-slate-400 tracking-[0.14em] uppercase">
                  <span className="w-2 h-2 rounded-full" style={{ background: '#22d3ee' }} />
                  Ledger Verified
                </span>
              </div>
            </div>
          </div>

          {/* Right panel */}
          <div className="w-full md:w-[460px] flex-shrink-0 flex flex-col items-center justify-center px-10 py-12"
               style={{ background: '#0a1628' }}>
            <div className="w-full max-w-[360px]">

              <h2 className="text-[26px] font-bold text-white text-center mb-1.5">
                Welcome Back
              </h2>
              <p className="text-[13px] text-slate-400 text-center mb-8">
                Enter credentials to access secure node
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">

                {/* Investigator ID */}
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 tracking-[0.22em] uppercase mb-1.5">
                    Investigator ID / Email
                  </label>
                  <div className="relative">
                    <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[15px] h-[15px] text-slate-500 pointer-events-none"
                         viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                    <input
                      type="text"
                      required
                      autoComplete="username"
                      autoFocus
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      disabled={loading}
                      placeholder="analyst@forensicchain.int"
                      className="fc-input w-full pl-[38px] pr-4 py-[11px] rounded-lg text-[13px]
                                 text-slate-200 placeholder-slate-600 transition-all
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{ background: '#05111f', border: '1px solid rgba(34,211,238,0.18)' }}
                    />
                  </div>
                </div>

                {/* Password */}
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 tracking-[0.22em] uppercase mb-1.5">
                    Access Token / Password
                  </label>
                  <div className="relative">
                    <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[15px] h-[15px] text-slate-500 pointer-events-none"
                         viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0110 0v4" />
                    </svg>
                    <input
                      type="password"
                      required
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={loading}
                      placeholder="••••••••••••"
                      className="fc-input w-full pl-[38px] pr-4 py-[11px] rounded-lg text-[13px]
                                 text-slate-200 placeholder-slate-600 transition-all
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{ background: '#05111f', border: '1px solid rgba(34,211,238,0.18)' }}
                    />
                  </div>

                  {error && (
                    <p className="flex items-center gap-1.5 text-[11px] text-red-400 mt-1.5">
                      <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                      </svg>
                      {error}
                    </p>
                  )}
                </div>

                {/* Remember + Recover */}
                <div className="flex items-center justify-between pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={remember}
                      onChange={(e) => setRemember(e.target.checked)}
                      className="w-3.5 h-3.5 rounded-sm cursor-pointer"
                      style={{ accentColor: '#22d3ee' }}
                    />
                    <span className="text-[13px] text-slate-400">Remember device</span>
                  </label>
                  <button type="button"
                          className="text-[13px] text-cyan-400 hover:text-cyan-300 transition-colors">
                    Recover identity?
                  </button>
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 rounded-lg text-[13px] font-semibold text-white
                             flex items-center justify-center gap-2
                             disabled:opacity-50 disabled:cursor-not-allowed
                             transition-all hover:brightness-110 active:scale-[0.99]"
                  style={{ background: 'linear-gradient(to right, #0ea5e9, #2563eb)' }}
                >
                  {loading ? (
                    <><Spinner /><span>Authenticating…</span></>
                  ) : (
                    <>
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                           strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4" />
                        <polyline points="10 17 15 12 10 7" />
                        <line x1="15" y1="12" x2="3" y2="12" />
                      </svg>
                      Secure Sign In
                    </>
                  )}
                </button>
              </form>

              {/* SSO divider */}
              <div className="my-6 flex items-center gap-3">
                <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.07)' }} />
                <span className="text-[10px] font-semibold text-slate-500 tracking-[0.22em] uppercase">
                  Institutional SSO
                </span>
                <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.07)' }} />
              </div>

              {/* SSO button */}
              <button
                type="button"
                className="w-full py-[11px] rounded-lg text-[13px] font-medium text-slate-300
                           flex items-center justify-center gap-2.5
                           hover:brightness-125 transition-all"
                style={{ background: '#0c1d30', border: '1px solid rgba(255,255,255,0.09)' }}
              >
                <svg className="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
                Continue with Institution SSO
              </button>

              {/* New facility */}
              <p className="mt-6 text-center text-[13px] text-slate-500">
                New facility?{' '}
                <button type="button"
                        className="text-cyan-400 hover:text-cyan-300 transition-colors font-medium">
                  Request access node
                </button>
              </p>

              {/* Footer notice */}
              <p className="mt-8 text-center text-[10px] text-slate-600 tracking-[0.18em] uppercase leading-relaxed">
                Authorized personnel only.<br />All access is logged and encrypted.
              </p>

            </div>
          </div>

        </div>

        {/* ── Bottom bar ────────────────────────────────────────────────── */}
        <div className="flex items-center justify-center gap-10 py-3.5"
             style={{ background: '#060d1a', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="flex items-center gap-2 text-slate-500 text-[11px]">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            ISO 27001 Certified
          </div>
          <div className="flex items-center gap-2 text-slate-500 text-[11px]">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Criminal Justice Info Services
          </div>
          <div className="flex items-center gap-2 text-slate-500 text-[11px]">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            AES-256 Encrypted
          </div>
        </div>

      </div>
    </>
  )
}
