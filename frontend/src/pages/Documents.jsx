import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentsAPI } from '../services/api'

const STATUS_COLORS = {
  uploaded: 'bg-slate-100 text-slate-600',
  processing: 'bg-blue-100 text-blue-700',
  extracted: 'bg-yellow-100 text-yellow-700',
  validated: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

function DocCard({ doc, onReprocess, onDelete }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">
            {doc.file_type === 'pdf' ? '📕' : doc.file_type?.match(/png|jpg|jpeg/) ? '🖼️' : '📄'}
          </span>
          <div>
            <div className="font-medium text-slate-800 text-sm truncate max-w-[200px]">{doc.filename}</div>
            <div className="text-xs text-slate-400 mt-0.5">
              {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : ''} ·{' '}
              {new Date(doc.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[doc.status] || STATUS_COLORS.uploaded}`}>
          {doc.status}
        </span>
      </div>

      <div className="flex gap-2 mt-3">
        <button onClick={() => setExpanded(e => !e)}
          className="text-xs px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded transition-colors">
          {expanded ? 'Hide' : 'View'} Data
        </button>
        <button onClick={() => onReprocess(doc.id)}
          className="text-xs px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors">
          Reprocess
        </button>
        <button onClick={() => onDelete(doc.id)}
          className="text-xs px-2 py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded transition-colors">
          Delete
        </button>
      </div>

      {expanded && doc.has_extracted_data && (
        <ExtractedDataView docId={doc.id} />
      )}
    </div>
  )
}

function ExtractedDataView({ docId }) {
  const { data, isLoading } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => documentsAPI.get(docId).then(r => r.data),
  })

  if (isLoading) return <div className="mt-3 text-xs text-slate-400">Loading...</div>
  if (!data) return null

  return (
    <div className="mt-3 space-y-3">
      {data.extracted_data && (
        <div>
          <div className="text-xs font-semibold text-slate-500 mb-1">Extracted Data</div>
          <pre className="text-xs bg-slate-50 rounded-lg p-3 overflow-auto max-h-48 text-slate-700">
            {JSON.stringify(data.extracted_data, null, 2)}
          </pre>
        </div>
      )}
      {data.validation_result && (
        <div>
          <div className="text-xs font-semibold text-slate-500 mb-1">Validation Result</div>
          <div className={`text-xs px-3 py-2 rounded-lg ${
            data.validation_result.validation_status === 'MATCH'
              ? 'bg-green-50 text-green-700'
              : 'bg-red-50 text-red-700'
          }`}>
            <div className="font-medium">{data.validation_result.validation_status}</div>
            <div className="mt-1">{data.validation_result.reason}</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Documents() {
  const qc = useQueryClient()
  const fileRef = useRef()
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const [filter, setFilter] = useState('')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents', filter],
    queryFn: () => documentsAPI.list(0, 50, filter).then(r => r.data),
    refetchInterval: 5000,
  })

  const reprocessMutation = useMutation({
    mutationFn: (id) => documentsAPI.reprocess(id),
    onSuccess: () => qc.invalidateQueries(['documents']),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => documentsAPI.delete(id),
    onSuccess: () => qc.invalidateQueries(['documents']),
  })

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMsg(null)
    try {
      await documentsAPI.upload(file)
      setUploadMsg({ type: 'success', text: 'Document uploaded! Processing started...' })
      qc.invalidateQueries(['documents'])
    } catch (err) {
      setUploadMsg({ type: 'error', text: err.response?.data?.detail || 'Upload failed' })
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Documents</h1>
          <p className="text-slate-500 text-sm">Upload invoices for AI extraction and validation</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt"
            className="hidden"
            onChange={handleUpload}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {uploading ? '⏳ Uploading...' : '📤 Upload Document'}
          </button>
        </div>
      </div>

      {uploadMsg && (
        <div className={`px-4 py-2 rounded-lg text-sm ${
          uploadMsg.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
          'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {uploadMsg.text}
          <button onClick={() => setUploadMsg(null)} className="ml-2 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2">
        {['', 'uploaded', 'processing', 'extracted', 'validated', 'failed'].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
              filter === s ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}>
            {s || 'All'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center text-slate-500 py-12">Loading documents...</div>
      ) : data?.items?.length === 0 ? (
        <div className="text-center text-slate-400 py-12">
          <div className="text-4xl mb-3">📂</div>
          <div>No documents yet. Upload a PDF or image to start.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items?.map(doc => (
            <DocCard
              key={doc.id}
              doc={doc}
              onReprocess={(id) => reprocessMutation.mutate(id)}
              onDelete={(id) => { if (confirm('Delete this document?')) deleteMutation.mutate(id) }}
            />
          ))}
        </div>
      )}

      <div className="text-sm text-slate-400">
        {data?.total || 0} documents total
      </div>
    </div>
  )
}
