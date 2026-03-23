import { useState, useEffect } from 'react'
import { getSummary } from '../api/client'

const Card = ({ label, value, sub, color }) => (
  <div style={{
    background: '#fff',
    borderRadius: '10px',
    padding: '24px',
    flex: 1,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    borderTop: `4px solid ${color}`,
  }}>
    <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '8px' }}>
      {label}
    </div>
    <div style={{ fontSize: '32px', fontWeight: 700, color: '#1f2937' }}>
      {value ?? '—'}
    </div>
    {sub && (
      <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
        {sub}
      </div>
    )}
  </div>
)

export default function SummaryCards() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSummary()
      .then(res => setData(res.data))
      .catch(err => console.error('Summary error:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', gap: '16px' }}>
      {[1,2,3,4].map(i => (
        <div key={i} style={{
          flex: 1,
          background: '#fff',
          borderRadius: '10px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        }}>
          <div style={{
            height: '12px',
            background: '#f3f4f6',
            borderRadius: '4px',
            marginBottom: '12px',
            width: '60%',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}/>
          <div style={{
            height: '28px',
            background: '#f3f4f6',
            borderRadius: '4px',
            width: '40%',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}/>
          <style>{`
            @keyframes pulse {
              0%, 100% { opacity: 1; }
              50% { opacity: 0.4; }
            }
          `}</style>
        </div>
      ))}
    </div>
  )

  const lastRun = data?.last_run_at
    ? new Date(data.last_run_at).toLocaleString()
    : 'Never'

  const avgPrice = data?.sources?.[0]?.avg_price
    ? `£${data.sources[0].avg_price}`
    : null

  return (
    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
      <Card
        label="Total Items Tracked"
        value={data?.total_items?.toLocaleString()}
        sub={`Across ${data?.total_sources} source(s)`}
        color="#6366f1"
      />
      <Card
        label="Scrape Runs"
        value={data?.total_scrape_runs}
        sub={`Last run: ${lastRun}`}
        color="#10b981"
      />
      <Card
        label="Average Price"
        value={avgPrice}
        sub="Current dataset"
        color="#f59e0b"
      />
      <Card
        label="Active Alerts"
        value={data?.active_alerts}
        sub="Configured monitors"
        color="#ef4444"
      />
    </div>
  )
}