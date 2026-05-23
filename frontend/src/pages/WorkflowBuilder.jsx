import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactFlow, {
  addEdge, MiniMap, Controls, Background,
  useNodesState, useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { workflowsAPI } from '../services/api'

const NODE_COLORS = {
  start: '#10b981',
  end: '#ef4444',
  ai_agent: '#3b82f6',
  approval: '#f59e0b',
  condition: '#8b5cf6',
}

const SAMPLE_YAML = `workflow:
  name: "Invoice Approval Flow"
  version: "1.0"
  steps:
    - id: start
      type: start
      next: extract_document

    - id: extract_document
      type: ai_agent
      agent: document_extractor
      on_success: validate_invoice
      on_failure: flag_error

    - id: validate_invoice
      type: ai_agent
      agent: validator
      on_success: route_approval
      on_failure: flag_error

    - id: route_approval
      type: condition
      rules:
        - if: "amount > 10000"
          next: manager_approval
        - if: "amount <= 10000"
          next: operator_approval

    - id: manager_approval
      type: approval
      assigned_role: Manager
      next: complete

    - id: operator_approval
      type: approval
      assigned_role: Operator
      next: complete

    - id: flag_error
      type: ai_agent
      agent: exception_detector
      next: complete

    - id: complete
      type: end`

function buildNodesEdges(steps) {
  if (!steps) return { nodes: [], edges: [] }
  const nodes = steps.map((step, i) => ({
    id: step.id,
    data: { label: `${step.id}\n(${step.type})` },
    position: { x: 150 * (i % 4), y: Math.floor(i / 4) * 120 },
    style: {
      background: NODE_COLORS[step.type] || '#64748b',
      color: 'white',
      border: 'none',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 11,
      minWidth: 120,
    },
  }))

  const edges = []
  for (const step of steps) {
    const addEdgeEntry = (target, label = '') => {
      if (target) edges.push({ id: `${step.id}-${target}`, source: step.id, target, label })
    }
    if (step.next) addEdgeEntry(step.next)
    if (step.on_success) addEdgeEntry(step.on_success, '✓')
    if (step.on_failure) addEdgeEntry(step.on_failure, '✗')
    for (const rule of step.rules || []) {
      if (rule.next) addEdgeEntry(rule.next, rule.if?.slice(0, 20))
    }
  }
  return { nodes, edges }
}

export default function WorkflowBuilder() {
  const qc = useQueryClient()
  const [yaml, setYaml] = useState(SAMPLE_YAML)
  const [name, setName] = useState('My Workflow')
  const [selectedWf, setSelectedWf] = useState(null)
  const [validationMsg, setValidationMsg] = useState(null)
  const [activeTab, setActiveTab] = useState('editor')

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const { data: wfList } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => workflowsAPI.list().then(r => r.data),
  })

  const saveMutation = useMutation({
    mutationFn: (data) => selectedWf
      ? workflowsAPI.update(selectedWf.id, data)
      : workflowsAPI.create(data),
    onSuccess: () => {
      qc.invalidateQueries(['workflows'])
      setValidationMsg({ type: 'success', text: 'Workflow saved successfully!' })
    },
    onError: (err) => {
      const detail = err.response?.data?.detail
      const msg = typeof detail === 'object' ? JSON.stringify(detail) : detail || 'Save failed'
      setValidationMsg({ type: 'error', text: msg })
    },
  })

  const runMutation = useMutation({
    mutationFn: (id) => workflowsAPI.run(id, {}),
    onSuccess: (data) => {
      setValidationMsg({ type: 'success', text: `Workflow run started: #${data.data.run_id}` })
    },
  })

  const handleYamlChange = (val) => {
    setYaml(val)
    try {
      const yamlModule = window.jsyaml
      if (yamlModule) {
        const parsed = yamlModule.load(val)
        if (parsed?.workflow?.steps) {
          const { nodes: n, edges: e } = buildNodesEdges(parsed.workflow.steps)
          setNodes(n)
          setEdges(e)
        }
      }
    } catch (e) {}
  }

  const handleValidate = async () => {
    try {
      const res = await workflowsAPI.validate(yaml)
      const v = res.data
      if (v.valid) {
        setValidationMsg({ type: 'success', text: `Valid! ${v.step_count} steps. ${v.warnings?.length ? 'Warnings: ' + v.warnings.join(', ') : ''}` })
        const { nodes: n, edges: e } = buildNodesEdges(parseSteps(yaml))
        setNodes(n)
        setEdges(e)
      } else {
        setValidationMsg({ type: 'error', text: 'Errors: ' + v.errors.join(', ') })
      }
    } catch (err) {
      setValidationMsg({ type: 'error', text: 'Validation request failed' })
    }
  }

  function parseSteps(yamlStr) {
    try {
      const lines = yamlStr.split('\n')
      const steps = []
      let cur = null
      for (const line of lines) {
        const idMatch = line.match(/^\s+- id:\s+(\S+)/)
        if (idMatch) { if (cur) steps.push(cur); cur = { id: idMatch[1], rules: [] } }
        if (cur) {
          const typeMatch = line.match(/^\s+type:\s+(\S+)/); if (typeMatch) cur.type = typeMatch[1]
          const nextMatch = line.match(/^\s+next:\s+(\S+)/); if (nextMatch) cur.next = nextMatch[1]
          const sMatch = line.match(/^\s+on_success:\s+(\S+)/); if (sMatch) cur.on_success = sMatch[1]
          const fMatch = line.match(/^\s+on_failure:\s+(\S+)/); if (fMatch) cur.on_failure = fMatch[1]
        }
      }
      if (cur) steps.push(cur)
      return steps
    } catch { return [] }
  }

  const handleSave = () => saveMutation.mutate({ name, yaml_config: yaml })

  const loadWorkflow = (wf) => {
    setSelectedWf(wf)
    setName(wf.name)
    setYaml(wf.yaml_config)
    const { nodes: n, edges: e } = buildNodesEdges(parseSteps(wf.yaml_config))
    setNodes(n)
    setEdges(e)
  }

  const onConnect = useCallback((params) => setEdges(eds => addEdge(params, eds)), [setEdges])

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Workflow Builder</h1>
          <p className="text-slate-500 text-sm">Design and execute AI-powered workflows</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleValidate}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors">
            Validate
          </button>
          <button onClick={handleSave} disabled={saveMutation.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
            {saveMutation.isPending ? 'Saving...' : 'Save'}
          </button>
          {selectedWf && (
            <button onClick={() => runMutation.mutate(selectedWf.id)} disabled={runMutation.isPending}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
              {runMutation.isPending ? 'Starting...' : '▶ Run'}
            </button>
          )}
        </div>
      </div>

      {validationMsg && (
        <div className={`px-4 py-2 rounded-lg text-sm ${
          validationMsg.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
          'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {validationMsg.text}
          <button onClick={() => setValidationMsg(null)} className="ml-2 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      <div className="grid grid-cols-4 gap-4 h-[calc(100vh-220px)]">
        {/* Saved Workflows */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 overflow-y-auto">
          <h3 className="font-semibold text-slate-700 mb-3 text-sm">Saved Workflows</h3>
          <div className="space-y-2">
            <button onClick={() => { setSelectedWf(null); setYaml(SAMPLE_YAML); setName('New Workflow') }}
              className="w-full text-left text-xs px-2 py-1.5 text-blue-600 hover:bg-blue-50 rounded">
              + New Workflow
            </button>
            {wfList?.items?.map(wf => (
              <button key={wf.id} onClick={() => loadWorkflow(wf)}
                className={`w-full text-left text-xs px-2 py-1.5 rounded truncate transition-colors ${
                  selectedWf?.id === wf.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-slate-50 text-slate-700'
                }`}>
                ⚡ {wf.name}
              </button>
            ))}
          </div>
        </div>

        {/* Main area */}
        <div className="col-span-3 flex flex-col gap-4">
          {/* Name input */}
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Workflow name..."
          />

          {/* Tabs */}
          <div className="flex gap-2">
            {['editor', 'canvas'].map(tab => (
              <button key={tab} onClick={() => {
                if (tab === 'canvas') {
                  const { nodes: n, edges: e } = buildNodesEdges(parseSteps(yaml))
                  setNodes(n); setEdges(e)
                }
                setActiveTab(tab)
              }}
                className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors capitalize ${
                  activeTab === tab ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'
                }`}>
                {tab === 'editor' ? '📝 YAML Editor' : '🔀 Canvas View'}
              </button>
            ))}
          </div>

          {activeTab === 'editor' ? (
            <textarea
              value={yaml}
              onChange={e => handleYamlChange(e.target.value)}
              className="flex-1 font-mono text-xs p-4 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none bg-slate-900 text-green-400"
              spellCheck={false}
              style={{ minHeight: '400px' }}
            />
          ) : (
            <div className="flex-1 border border-slate-200 rounded-xl overflow-hidden bg-white" style={{ minHeight: '400px' }}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                fitView
              >
                <MiniMap />
                <Controls />
                <Background />
              </ReactFlow>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
