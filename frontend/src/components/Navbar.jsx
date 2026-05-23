import { NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { authAPI, approvalsAPI } from '../services/api'

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/workflows', label: 'Workflows', icon: '⚡' },
  { path: '/documents', label: 'Documents', icon: '📄' },
  { path: '/approvals', label: 'Approvals', icon: '✅' },
  { path: '/exceptions', label: 'Exceptions', icon: '⚠️' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
]

export default function Navbar() {
  const navigate = useNavigate()
  const user = JSON.parse(localStorage.getItem('nova_user') || '{}')

  const { data: pendingData } = useQuery({
    queryKey: ['pending-count'],
    queryFn: () => approvalsAPI.pendingCount().then(r => r.data),
    refetchInterval: 30000,
  })

  const handleLogout = async () => {
    try {
      await authAPI.logout()
    } catch (e) {}
    localStorage.removeItem('nova_token')
    localStorage.removeItem('nova_user')
    navigate('/login')
  }

  return (
    <aside className="w-56 bg-slate-900 text-white flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🚀</span>
          <div>
            <div className="font-bold text-lg leading-none">Nova</div>
            <div className="text-xs text-slate-400">AI Logistics Platform</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ path, label, icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            <span>{label}</span>
            {label === 'Approvals' && pendingData?.pending > 0 && (
              <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[20px] text-center">
                {pendingData.pending}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User info */}
      <div className="p-3 border-t border-slate-700">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold">
            {(user.name || 'U')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium truncate">{user.name || 'User'}</div>
            <div className="text-xs text-slate-400 truncate capitalize">{user.role || 'operator'}</div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full text-xs text-slate-400 hover:text-white py-1 text-left transition-colors"
        >
          → Sign out
        </button>
      </div>
    </aside>
  )
}
