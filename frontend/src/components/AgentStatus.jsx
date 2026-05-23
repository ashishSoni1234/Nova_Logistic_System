import { useQuery } from '@tanstack/react-query'
import { agentsAPI } from '../services/api'

export default function AgentStatus() {
  const { data } = useQuery({
    queryKey: ['agent-status'],
    queryFn: () => agentsAPI.status().then(r => r.data),
    refetchInterval: 60000,
  })

  if (!data) return null

  const allReady = Object.values(data.rag_collections || {}).every(c => c.ready)

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`w-2 h-2 rounded-full ${allReady ? 'bg-green-500' : 'bg-yellow-500'}`} />
      <span className="text-slate-500">
        RAG: {allReady ? 'Ready' : 'Data needed'}
      </span>
    </div>
  )
}
