import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getItemTrend } from '../api/client'

export default function PriceChart({ item }) {
  const [trend, setTrend] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!item) return
    setLoading(true)
    getItemTrend(item.id)
      .then(res => setTrend(res.data))
      .catch(err => console.error('Trend error:', err))
      .finally(() => setLoading(false))
  }, [item])

  if (!item) return (
    <div style={{
      background: '#fff',
      borderRadius: '10px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      padding: '40px',
      textAlign: 'center',
      color: '#9ca3af',
      fontSize: '14px',
    }}>
      Click any row in the table to see its price history
    </div>
  )

  if (loading) return (
    <div style={{
      background: '#fff',
      borderRadius: '10px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      padding: '40px',
      textAlign: 'center',
      color: '#9ca3af',
    }}>
      Loading chart...
    </div>
  )

  const chartData = trend?.snapshots?.map(s => ({
    time: new Date(s.scraped_at).toLocaleTimeString(),
    price: s.price,
  })) || []

  return (
    <div style={{
      background: '#fff',
      borderRadius: '10px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      padding: '24px',
    }}>

      {/* Chart header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontSize: '15px', fontWeight: 600, color: '#1f2937' }}>
          {trend?.item_title}
        </div>
        <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
          Price history — {chartData.length} data points
        </div>
      </div>

      {/* Stat pills */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {[
          { label: 'Current', value: `£${trend?.current_price}`, color: '#6366f1' },
          { label: 'Min',     value: `£${trend?.min_price}`,     color: '#10b981' },
          { label: 'Max',     value: `£${trend?.max_price}`,     color: '#ef4444' },
          { label: 'Avg',     value: `£${trend?.avg_price}`,     color: '#f59e0b' },
        ].map(stat => (
          <div key={stat.label} style={{
            background: '#f9fafb',
            borderRadius: '8px',
            padding: '10px 16px',
            borderLeft: `3px solid ${stat.color}`,
          }}>
            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>
              {stat.label}
            </div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#1f2937' }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* Line chart */}
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `£${v}`}
            domain={['auto', 'auto']}
          />
          <Tooltip
            formatter={(value) => [`£${value}`, 'Price']}
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '13px',
            }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#6366f1"
            strokeWidth={2.5}
            dot={{ fill: '#6366f1', r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}