import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { approvalsAPI } from '../services/api'

const STATUS_CONFIG = {
  pending: { bg: 'bg-yellow-100 text-yellow-700', label: 'Pending' },
  approved: { bg: 'bg-green-100 text-green-700', label: 'Approved' },
  rejected: { bg: 'bg-red-100 text-red-700', label: 'Rejected' },
  escalated: { bg: 'bg-purple-100 text-purple-700', label: 'Escalated' },
}

function ApprovalCard({ approval, onAction }) {
  const [comment, setComment] = useState('')
  const [showComment, setShowComment] = useState(false)
  const cfg = STATUS_CONFIG[approval.status] || STATUS_CONFIG.pending
  const isPending = approval.status === 'pending'

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-slate-800">{approval.title}</h3>
          {approval.description && (
            <p className="text-sm text-slate-500 mt-0.5">{approval.description}</p>
          )}
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${cfg.bg}`}>
          {cfg.label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
        {approval.amount && (
          <div>
            <span className="text-slate-400 text-xs">Amount</span>
            <div className="font-medium text-slate-700">${approval.amount}</div>
          </div>
        )}
        <div>
          <span className="text-slate-400 text-xs">Role</span>
          <div className="font-medium text-slate-700">{approval.assigned_role || '—'}</div>
        </div>
        <div>
          <span className="text-slate-400 text-xs">Created</span>
          <div className="font-medium text-slate-700">
            {new Date(approval.created_at).toLocaleDateString()}
          </div>
        </div>
        {approval.comment && (
          <div className="col-span-2">
            <span className="text-slate-400 text-xs">Comment</span>
            <div className="font-medium text-slate-700">{approval.comment}</div>
          </div>
        )}
      </div>

      {isPending && (
        <div className="space-y-2">
          {showComment && (
            <textarea
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="Add a comment (optional)..."
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={2}
            />
          )}
          <div className="flex gap-2">
            <button
              onClick={() => onAction(approval.id, 'approve', comment)}
              className="flex-1 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg font-medium transition-colors"
            >
              ✓ Approve
            </button>
            <button
              onClick={() => onAction(approval.id, 'reject', comment)}
              className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg font-medium transition-colors"
            >
              ✗ Reject
            </button>
            <button
              onClick={() => setShowComment(s => !s)}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm rounded-lg transition-colors"
            >
              💬
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Approvals() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState('')
  const [msg, setMsg] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['approvals', filter],
    queryFn: () => approvalsAPI.list(0, 50, filter).then(r => r.data),
    refetchInterval: 10000,
  })

  const actionMutation = useMutation({
    mutationFn: ({ id, action, comment }) => approvalsAPI.action(id, action, comment),
    onSuccess: (_, vars) => {
      qc.invalidateQueries(['approvals'])
      qc.invalidateQueries(['pending-count'])
      setMsg({ type: 'success', text: `Approval ${vars.action}d successfully` })
      setTimeout(() => setMsg(null), 3000)
    },
    onError: (err) => {
      setMsg({ type: 'error', text: err.response?.data?.detail || 'Action failed' })
    },
  })

  const pending = data?.items?.filter(a => a.status === 'pending') || []
  const resolved = data?.items?.filter(a => a.status !== 'pending') || []

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Approvals</h1>
        <p className="text-slate-500 text-sm">Review and act on pending workflow approvals</p>
      </div>

      {msg && (
        <div className={`px-4 py-2 rounded-lg text-sm ${
          msg.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
          'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {msg.text}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2">
        {[
          { val: '', label: 'All' },
          { val: 'pending', label: `Pending (${pending.length})` },
          { val: 'approved', label: 'Approved' },
          { val: 'rejected', label: 'Rejected' },
        ].map(({ val, label }) => (
          <button key={val} onClick={() => setFilter(val)}
            className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
              filter === val ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}>
            {label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center text-slate-500 py-12">Loading approvals...</div>
      ) : data?.items?.length === 0 ? (
        <div className="text-center text-slate-400 py-12">
          <div className="text-4xl mb-3">✅</div>
          <div>No approvals found</div>
        </div>
      ) : (
        <div className="space-y-6">
          {pending.length > 0 && !filter && (
            <div>
              <h2 className="text-sm font-semibold text-slate-500 uppercase mb-3">
                Pending ({pending.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {pending.map(a => (
                  <ApprovalCard key={a.id} approval={a}
                    onAction={(id, action, comment) => actionMutation.mutate({ id, action, comment })} />
                ))}
              </div>
            </div>
          )}

          {(filter ? data.items : resolved).length > 0 && (
            <div>
              {!filter && <h2 className="text-sm font-semibold text-slate-500 uppercase mb-3">History</h2>}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(filter ? data.items : resolved).map(a => (
                  <ApprovalCard key={a.id} approval={a}
                    onAction={(id, action, comment) => actionMutation.mutate({ id, action, comment })} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
