import { Link } from 'react-router-dom'
import Layout from '../components/Layout'
import { useAuth } from '../hooks/useAuth'

export default function DashboardPage() {
  const { username, role } = useAuth()

  return (
    <Layout>
      <div className="max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Dashboard</h1>
        <p className="text-sm text-gray-500 mb-8">
          Signed in as{' '}
          <span className="font-medium text-gray-700">{username}</span>{' '}
          <span className="text-gray-400">({role})</span>
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link
            to="/artifacts/upload"
            className="block rounded-xl border border-gray-200 bg-white p-6 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <p className="font-semibold text-gray-900">Upload Evidence</p>
            <p className="mt-1 text-sm text-gray-500">
              Ingest a new artifact — hash, sign, and seal it in the ledger
            </p>
          </Link>

          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <p className="font-semibold text-gray-900 mb-2">Inspect Artifact</p>
            <p className="text-sm text-gray-500 mb-3">
              Navigate directly to an artifact by ID:
            </p>
            <code className="block text-xs bg-gray-50 border border-gray-200 rounded-md px-3 py-2 text-gray-600">
              /artifacts/&#x3C;artifact-id&#x3E;
            </code>
          </div>
        </div>
      </div>
    </Layout>
  )
}
