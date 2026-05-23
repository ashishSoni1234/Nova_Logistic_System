const yamlStr = `workflow:
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
      on_failure: flag_error`;

const NODE_COLORS = {
  start: '#10b981',
  end: '#ef4444',
  ai_agent: '#3b82f6',
  approval: '#f59e0b',
  condition: '#8b5cf6',
}

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

const lines = yamlStr.split('\n');
const steps = [];
let cur = null;
for (const line of lines) {
  const idMatch = line.match(/^\s+- id:\s+(\S+)/);
  if (idMatch) { if (cur) steps.push(cur); cur = { id: idMatch[1], rules: [] } }
  if (cur) {
    const typeMatch = line.match(/^\s+type:\s+(\S+)/); if (typeMatch) cur.type = typeMatch[1]
    const nextMatch = line.match(/^\s+next:\s+(\S+)/); if (nextMatch) cur.next = nextMatch[1]
    const sMatch = line.match(/^\s+on_success:\s+(\S+)/); if (sMatch) cur.on_success = sMatch[1]
    const fMatch = line.match(/^\s+on_failure:\s+(\S+)/); if (fMatch) cur.on_failure = fMatch[1]
  }
}
if (cur) steps.push(cur);

const res = buildNodesEdges(steps);
console.log(JSON.stringify(res, null, 2));
