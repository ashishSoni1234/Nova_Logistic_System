import { useQuery } from '@tanstack/react-query'
import { dashboardAPI } from '../services/api'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b']

function StatCard({ title, value, icon, color = 'blue', subtitle }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  }
  return (
    <div className={`rounded-xl border p-5 ${colors[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium opacity-80">{title}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="text-3xl font-bold">{value ?? '—'}</div>
      {subtitle && <div className="text-xs mt-1 opacity-70">{subtitle}</div>}
    </div>
  )
}

export default function Dashboard() {
  const user = JSON.parse(localStorage.getItem('nova_user') || '{}')

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardAPI.getSummary().then(r => r.data),
    refetchInterval: 60000,
  })

  const { data: shipments } = useQuery({
    queryKey: ['shipments-time'],
    queryFn: () => dashboardAPI.getShipmentsOverTime(20).then(r => r.data),
  })

  const { data: approvalStatus } = useQuery({
    queryKey: ['approval-status'],
    queryFn: () => dashboardAPI.getApprovalStatus().then(r => r.data),
  })

  const { data: exceptionTrend } = useQuery({
    queryKey: ['exception-trend'],
    queryFn: () => dashboardAPI.getExceptionTrend(14).then(r => r.data),
  })

  const { data: categories } = useQuery({
    queryKey: ['category-breakdown'],
    queryFn: () => dashboardAPI.getCategoryBreakdown().then(r => r.data),
  })

  const { data: activity } = useQuery({
    queryKey: ['recent-activity'],
    queryFn: () => dashboardAPI.getRecentActivity().then(r => r.data),
  })

  if (summaryLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-slate-500 text-lg">Loading dashboard...</div>
      </div>
    )
  }

  const s = summary || {}

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">
          Welcome back, {user.name} · {user.tenant_name}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Workflows" value={s.total_workflows} icon="⚡" color="blue" />
        <StatCard title="Pending Approvals" value={s.pending_approvals} icon="✅" color="yellow"
          subtitle="Awaiting your action" />
        <StatCard title="Open Exceptions" value={s.open_exceptions} icon="⚠️" color="red"
          subtitle={`${s.exceptions_today || 0} today`} />
        <StatCard title="SC Records" value={s.total_supply_chain_records?.toLocaleString()} icon="📦" color="green"
          subtitle="DataCo dataset" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Documents" value={s.total_documents} icon="📄" color="purple" />
        <StatCard title="Active Runs" value={s.active_runs} icon="🔄" color="blue" />
        <StatCard title="Exceptions Today" value={s.exceptions_today} icon="🔔" color="red" />
        <StatCard title="Platform" value="Online" icon="🚀" color="green" subtitle="All systems operational" />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Shipments over time */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Shipments Over Time</h2>
          {shipments?.data?.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={shipments.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v?.slice(5) || v} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="shipments" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-400 text-sm">
              Load DataCo dataset to see shipment data
            </div>
          )}
        </div>

        {/* Approval Status Pie */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Approval Status</h2>
          {approvalStatus?.data?.some(d => d.count > 0) ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={approvalStatus.data.filter(d => d.count > 0)}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ status, count }) => `${status}: ${count}`}
                >
                  {approvalStatus.data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-400 text-sm">
              No approval data yet
            </div>
          )}
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Exception Trend */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Exception Trend (14 days)</h2>
          {exceptionTrend?.data?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={exceptionTrend.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => v?.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="exceptions" stroke="#ef4444" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-slate-400 text-sm">
              No exception data yet
            </div>
          )}
        </div>

        {/* Category Breakdown */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Top Categories</h2>
          {categories?.data?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={categories.data.slice(0, 6)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis dataKey="category" type="category" tick={{ fontSize: 10 }} width={100} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-slate-400 text-sm">
              Load DataCo dataset to see categories
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-700 mb-4">Recent Activity</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Runs */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">Workflow Runs</h3>
            <div className="space-y-2">
              {activity?.recent_runs?.length > 0 ? activity.recent_runs.map(r => (
                <div key={r.id} className="flex items-center gap-2 text-sm">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    r.status === 'completed' ? 'bg-green-500' :
                    r.status === 'failed' ? 'bg-red-500' :
                    r.status === 'running' ? 'bg-blue-500' : 'bg-yellow-500'
                  }`} />
                  <span className="text-slate-600 truncate">Run #{r.id}</span>
                  <span className="ml-auto text-xs text-slate-400 capitalize">{r.status}</span>
                </div>
              )) : <p className="text-sm text-slate-400">No recent runs</p>}
            </div>
          </div>

          {/* Recent Documents */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">Documents</h3>
            <div className="space-y-2">
              {activity?.recent_documents?.length > 0 ? activity.recent_documents.map(d => (
                <div key={d.id} className="flex items-center gap-2 text-sm">
                  <span className="text-slate-400">📄</span>
                  <span className="text-slate-600 truncate flex-1">{d.filename}</span>
                  <span className="text-xs text-slate-400 capitalize">{d.status}</span>
                </div>
              )) : <p className="text-sm text-slate-400">No recent documents</p>}
            </div>
          </div>

          {/* Recent Exceptions */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">Exceptions</h3>
            <div className="space-y-2">
              {activity?.recent_exceptions?.length > 0 ? activity.recent_exceptions.map(e => (
                <div key={e.id} className="text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      e.severity === 'critical' ? 'bg-red-600' :
                      e.severity === 'high' ? 'bg-red-400' :
                      e.severity === 'medium' ? 'bg-yellow-400' : 'bg-blue-400'
                    }`} />
                    <span className="text-slate-600 truncate">{e.reason}</span>
                  </div>
                </div>
              )) : <p className="text-sm text-slate-400">No recent exceptions</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
