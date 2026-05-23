import { BrowserRouter, Routes, Route, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import WorkflowBuilder from './pages/WorkflowBuilder'
import Documents from './pages/Documents'
import Approvals from './pages/Approvals'
import Exceptions from './pages/Exceptions'
import Settings from './pages/Settings'
import Navbar from './components/Navbar'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
    },
  },
})

// Single shared layout — Navbar mounts ONCE, never remounts on route change
function ProtectedLayout() {
  const navigate = useNavigate()

  useEffect(() => {
    const handleLogout = () => navigate('/login', { replace: true })
    window.addEventListener('nova_logout', handleLogout)
    return () => window.removeEventListener('nova_logout', handleLogout)
  }, [navigate])

  if (!localStorage.getItem('nova_token')) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex h-screen bg-slate-100">
      <Navbar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* All protected pages share ONE layout — Navbar mounts only once */}
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/workflows" element={<WorkflowBuilder />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/approvals" element={<Approvals />} />
            <Route path="/exceptions" element={<Exceptions />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
