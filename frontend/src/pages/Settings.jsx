import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { agentsAPI } from '../services/api'

export default function Settings() {
  const user = JSON.parse(localStorage.getItem('nova_user') || '{}')
  const [ragQuery, setRagQuery] = useState('')
  const [ragResult, setRagResult] = useState(null)
  const [ragLoading, setRagLoading] = useState(false)

  const { data: agentStatus } = useQuery({
    queryKey: ['agent-status'],
    queryFn: () => agentsAPI.status().then(r => r.data),
  })

  const handleRagQuery = async () => {
    if (!ragQuery.trim()) return
    setRagLoading(true)
    try {
      const res = await agentsAPI.ragQuery(ragQuery)
      setRagResult(res.data.result)
    } catch (err) {
      setRagResult({ answer: 'Query failed: ' + (err.response?.data?.detail || err.message), error: true })
    } finally {
      setRagLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
        <p className="text-slate-500 text-sm">System status and configuration</p>
      </div>

      {/* User Info */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-700 mb-4">Account</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            { label: 'Name', value: user.name },
            { label: 'Email', value: user.email },
            { label: 'Role', value: user.role },
            { label: 'Company', value: user.tenant_name },
          ].map(({ label, value }) => (
            <div key={label}>
              <div className="text-slate-400 text-xs">{label}</div>
              <div className="font-medium text-slate-700 capitalize">{value || '—'}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Agent Status */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-700 mb-4">AI Agent Status</h2>
        {agentStatus ? (
          <div className="space-y-4">
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">Agents</h3>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(agentStatus.agents || {}).map(([name, status]) => (
                  <div key={name} className="flex items-center gap-2 text-sm">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-slate-700 capitalize">{name.replace(/_/g, ' ')}</span>
                    <span className="ml-auto text-xs text-green-600">{status}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2">RAG Collections</h3>
              <div className="space-y-2">
                {Object.entries(agentStatus.rag_collections || {}).map(([key, info]) => (
                  <div key={key} className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${info.ready ? 'bg-green-500' : 'bg-slate-300'}`} />
                    <span className="text-slate-700">{key}</span>
                    <span className="ml-auto text-xs text-slate-400">{info.documents} docs</span>
                    <span className={`text-xs ${info.ready ? 'text-green-600' : 'text-slate-400'}`}>
                      {info.ready ? 'Ready' : 'Empty'}
                    </span>
                  </div>
                ))}
              </div>
              {!Object.values(agentStatus.rag_collections || {}).some(c => c.ready) && (
                <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-700">
                  RAG collections are empty. Run the data loaders to populate them:
                  <pre className="mt-1 font-mono">cd backend && python data_loaders/load_sroie.py</pre>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-400">Loading agent status...</div>
        )}
      </div>

      {/* RAG Query Tester */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-700 mb-4">RAG Query Tester</h2>
        <div className="flex gap-2 mb-4">
          <input
            value={ragQuery}
            onChange={e => setRagQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleRagQuery()}
            placeholder="Ask a question about your logistics data..."
            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleRagQuery}
            disabled={ragLoading || !ragQuery.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg font-medium transition-colors"
          >
            {ragLoading ? '...' : 'Ask'}
          </button>
        </div>

        {ragResult && (
          <div className={`p-4 rounded-lg text-sm ${ragResult.error ? 'bg-red-50 text-red-700' : 'bg-slate-50 text-slate-700'}`}>
            <div className="font-medium mb-2">Answer:</div>
            <div className="whitespace-pre-wrap">{ragResult.answer}</div>
            {ragResult.contexts_used !== undefined && (
              <div className="mt-2 text-xs text-slate-400">
                Used {ragResult.contexts_used} context chunks from: {ragResult.sources?.join(', ')}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Setup Guide */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-700 mb-4">Setup Guide</h2>
        <div className="space-y-3 text-sm text-slate-600">
          <div className="p-3 bg-slate-50 rounded-lg font-mono text-xs space-y-1">
            <div className="text-slate-500"># 1. Start Docker services</div>
            <div>cd infra && docker-compose up -d</div>
            <div className="text-slate-500 mt-2"># 2. Install Python dependencies</div>
            <div>cd backend && pip install -r requirements.txt</div>
            <div className="text-slate-500 mt-2"># 3. Add Groq API key to .env</div>
            <div>GROQ_API_KEY=gsk_...</div>
            <div className="text-slate-500 mt-2"># 4. Start backend</div>
            <div>cd backend && python main.py</div>
            <div className="text-slate-500 mt-2"># 5. Load datasets (optional, takes time)</div>
            <div>python data_loaders/load_sroie.py</div>
            <div>python data_loaders/load_fraud.py</div>
            <div>python data_loaders/load_dataco.py</div>
          </div>
        </div>
      </div>
    </div>
  )
}
