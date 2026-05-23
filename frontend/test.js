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
console.log(steps);
