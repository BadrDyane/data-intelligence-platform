import { useState, useEffect } from 'react'
import { getRuns } from '../api/client'

const STATUS_CONFIG = {
  success: { color: '#10b981', bg: '#d1fae5', label: 'Success' },
  partial: { color: '#f59e0b', bg: '#fef3c7', label: 'Partial' },
  failed:  { color: '#ef4444', bg: '#fee2e2', label: 'Failed'  },
  running: { color: '#6366f1', bg: '#eef2ff', label: 'Running' },
  pending: { color: '#9ca3af', bg: '#f3f4f6', label: 'Pending' },
}

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return (
    <span style={{
      background: config.bg,
      color: config.color,
      borderRadius: '20px',
      padding: '3px 10px',
      fontSize: '12px',
      fontWeight: 600,
    }}>
      {config.label}
    </span>
  )
}

function duration(seconds) {
  if (!seconds) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function timeAgo(dateStr) {
  if (!dateStr) return '—'
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60)   return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function Runs() {
  const [runs, setRuns]       = useState([])
  const [loading, setLoading] = useState(true)

  const fetchRuns = () => {
    setLoading(true)
    getRuns()
      .then(res => setRuns(res.data))
      .catch(err => console.error('Runs error:', err))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchRuns() }, [])

  return (
    <div style={{ padding: '32px' }}>

      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '32px',
      }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1f2937' }}>
            Scrape Runs
          </h1>
          <p style={{ color: '#6b7280', marginTop: '4px' }}>
            Full job history — every scrape run recorded
          </p>
        </div>
        <button
          onClick={fetchRuns}
          style={{
            padding: '8px 16px',
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '13px',
            cursor: 'pointer',
            color: '#374151',
            fontWeight: 500,
          }}
        >
          Refresh
        </button>
      </div>

      {/* Runs table */}
      <div style={{
        background: '#fff',
        borderRadius: '10px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        overflow: 'hidden',
      }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
            Loading runs...
          </div>
        ) : runs.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
            No scrape runs yet — trigger one from the Dashboard
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                {['Run ID', 'Source', 'Status', 'Triggered', 'Duration', 'Found', 'New', 'Updated', 'Errors'].map(h => (
                  <th key={h} style={{
                    padding: '12px 16px',
                    textAlign: 'left',
                    fontSize: '12px',
                    fontWeight: 600,
                    color: '#6b7280',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    borderBottom: '1px solid #f3f4f6',
                    whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => (
                <tr
                  key={run.id}
                  style={{ background: i % 2 === 0 ? '#fff' : '#fafafa' }}
                >
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#9ca3af' }}>
                    #{run.id}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#1f2937', fontWeight: 500 }}>
                    {run.source}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <StatusBadge status={run.status} />
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>
                    {timeAgo(run.started_at)}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>
                    {duration(run.duration_seconds)}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#1f2937', fontWeight: 600 }}>
                    {run.items_found}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#10b981', fontWeight: 600 }}>
                    {run.items_new > 0 ? `+${run.items_new}` : run.items_new}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6366f1' }}>
                    {run.items_updated}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: run.error_count > 0 ? '#ef4444' : '#9ca3af' }}>
                    {run.error_count > 0 ? `⚠ ${run.error_count}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}