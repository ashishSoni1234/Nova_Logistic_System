import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { exceptionsAPI } from '../services/api'

const SEVERITY_CONFIG = {
  low: { bg: 'bg-blue-100 text-blue-700', icon: 'ℹ️' },
  medium: { bg: 'bg-yellow-100 text-yellow-700', icon: '⚠️' },
  high: { bg: 'bg-orange-100 text-orange-700', icon: '🔥' },
  critical: { bg: 'bg-red-100 text-red-700', icon: '🚨' },
}

function ExceptionCard({ exc, onResolve }) {
  const cfg = SEVERITY_CONFIG[exc.severity] || SEVERITY_CONFIG.medium

  return (
    <div className={`bg-white rounded-xl border ${exc.resolved ? 'border-slate-200 opacity-70' : 'border-slate-200'} p-4`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span>{cfg.icon}</span>
          <span className="font-medium text-slate-800 text-sm capitalize">{exc.exception_type}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg}`}>
            {exc.severity}
          </span>
          {exc.resolved && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
              Resolved
            </span>
          )}
        </div>
      </div>

      <p className="text-sm text-slate-600 mb-3 line-clamp-2">{exc.reason}</p>

      <div className="text-xs text-slate-400 mb-3">
        {new Date(exc.created_at).toLocaleString()}
        {exc.workflow_run_id && ` · Run #${exc.workflow_run_id}`}
      </div>

      {!exc.resolved && (
        <button
          onClick={() => onResolve(exc.id)}
          className="w-full py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg font-medium transition-colors"
        >
          Mark Resolved
        </button>
      )}
    </div>
  )
}

export default function Exceptions() {
  const qc = useQueryClient()
  const [showResolved, setShowResolved] = useState(false)
  const [msg, setMsg] = useState(null)

  const { data: stats } = useQuery({
    queryKey: ['exception-stats'],
    queryFn: () => exceptionsAPI.stats().then(r => r.data),
    refetchInterval: 15000,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['exceptions', showResolved],
    queryFn: () => exceptionsAPI.list(0, 50, showResolved ? null : false).then(r => r.data),
    refetchInterval: 10000,
  })

  const resolveMutation = useMutation({
    mutationFn: (id) => exceptionsAPI.resolve(id),
    onSuccess: () => {
      qc.invalidateQueries(['exceptions'])
      qc.invalidateQueries(['exception-stats'])
      setMsg({ type: 'success', text: 'Exception resolved' })
      setTimeout(() => setMsg(null), 3000)
    },
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Exceptions</h1>
        <p className="text-slate-500 text-sm">Monitor and resolve detected anomalies and exceptions</p>
      </div>

      {msg && (
        <div className={`px-4 py-2 rounded-lg text-sm ${
          msg.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
          'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {msg.text}
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Total', value: stats.total, color: 'bg-slate-100 text-slate-700' },
            { label: 'Unresolved', value: stats.unresolved, color: 'bg-yellow-100 text-yellow-700' },
            { label: 'High Priority', value: stats.high, color: 'bg-orange-100 text-orange-700' },
            { label: 'Critical', value: stats.critical, color: 'bg-red-100 text-red-700' },
          ].map(({ label, value, color }) => (
            <div key={label} className={`rounded-xl p-4 ${color}`}>
              <div className="text-2xl font-bold">{value}</div>
              <div className="text-xs font-medium opacity-70">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Toggle */}
      <div className="flex items-center gap-3">
        <button onClick={() => setShowResolved(false)}
          className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
            !showResolved ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200'
          }`}>
          Open
        </button>
        <button onClick={() => setShowResolved(true)}
          className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
            showResolved ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200'
          }`}>
          All
        </button>
      </div>

      {isLoading ? (
        <div className="text-center text-slate-500 py-12">Loading exceptions...</div>
      ) : data?.items?.length === 0 ? (
        <div className="text-center text-slate-400 py-12">
          <div className="text-4xl mb-3">✅</div>
          <div>No {showResolved ? '' : 'open '}exceptions</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items?.map(exc => (
            <ExceptionCard
              key={exc.id}
              exc={exc}
              onResolve={(id) => resolveMutation.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
