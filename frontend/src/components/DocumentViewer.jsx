export default function DocumentViewer({ data }) {
  if (!data) return null
  return (
    <pre className="text-xs bg-slate-50 rounded-lg p-3 overflow-auto max-h-64 text-slate-700">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}
