import { useState, useEffect } from 'react'
import { getAlerts, deleteAlert } from '../api/client'

const CONDITION_LABELS = {
  price_below: 'Price drops below',
  price_above: 'Price rises above',
  price_drop:  'Price drops by %',
}

function timeAgo(dateStr) {
  if (!dateStr) return '—'
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60)    return `${diff}s ago`
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function Alerts() {
  const [alerts, setAlerts]   = useState([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)

  const fetchAlerts = () => {
    setLoading(true)
    getAlerts()
      .then(res => setAlerts(res.data))
      .catch(err => console.error('Alerts error:', err))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchAlerts() }, [])

  const handleDelete = async (id) => {
    setDeleting(id)
    try {
      await deleteAlert(id)
      setAlerts(prev => prev.filter(a => a.id !== id))
    } catch (err) {
      console.error('Delete error:', err)
    } finally {
      setDeleting(null)
    }
  }

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
            Price Alerts
          </h1>
          <p style={{ color: '#6b7280', marginTop: '4px' }}>
            Monitoring rules — checked after every scrape run
          </p>
        </div>
        <button
          onClick={fetchAlerts}
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

      {/* Alerts list */}
      <div style={{
        background: '#fff',
        borderRadius: '10px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        overflow: 'hidden',
      }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
            Loading alerts...
          </div>
        ) : alerts.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
            No alerts yet — click any book in the Dashboard and hit "Set Alert"
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                {['Label', 'Condition', 'Threshold', 'Status', 'Created', 'Last Fired', ''].map(h => (
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
              {alerts.map((alert, i) => (
                <tr
                  key={alert.id}
                  style={{ background: i % 2 === 0 ? '#fff' : '#fafafa' }}
                >
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#1f2937', fontWeight: 500, maxWidth: '220px' }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {alert.label || `Alert #${alert.id}`}
                    </div>
                    <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
                      Item #{alert.item_id}
                    </div>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>
                    {CONDITION_LABELS[alert.condition] || alert.condition}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', fontWeight: 600, color: '#1f2937' }}>
                    {alert.condition === 'price_drop'
                      ? `${alert.threshold}%`
                      : `£${alert.threshold}`}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      background: alert.status === 'active' ? '#d1fae5' : '#f3f4f6',
                      color: alert.status === 'active' ? '#059669' : '#6b7280',
                      borderRadius: '20px',
                      padding: '3px 10px',
                      fontSize: '12px',
                      fontWeight: 600,
                    }}>
                      {alert.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>
                    {timeAgo(alert.created_at)}
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>
                    {alert.last_fired_at ? timeAgo(alert.last_fired_at) : '—'}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <button
                      onClick={() => handleDelete(alert.id)}
                      disabled={deleting === alert.id}
                      style={{
                        padding: '5px 12px',
                        background: 'none',
                        border: '1px solid #fca5a5',
                        borderRadius: '6px',
                        color: '#ef4444',
                        fontSize: '12px',
                        cursor: deleting === alert.id ? 'not-allowed' : 'pointer',
                        opacity: deleting === alert.id ? 0.5 : 1,
                      }}
                    >
                      {deleting === alert.id ? 'Deleting...' : 'Delete'}
                    </button>
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