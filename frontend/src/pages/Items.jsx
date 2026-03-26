import { useState, useEffect } from 'react'
import { getItems, getItemTrend, getAlerts } from '../api/client'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const SOURCE_LABELS = {
  books_toscrape:  'Books',
  quotes_toscrape: 'Quotes',
}

function timeAgo(dateStr) {
  if (!dateStr) return '—'
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60)    return `${diff}s ago`
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function DetailPanel({ item, onClose }) {
  const [trend, setTrend]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!item) return
    setLoading(true)
    getItemTrend(item.id)
      .then(res => setTrend(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
  }, [item])

  const chartData = trend?.snapshots?.map(s => ({
    time:  new Date(s.scraped_at).toLocaleTimeString(),
    price: s.price,
  })) || []

  return (
    <div style={{
      width: '380px',
      flexShrink: 0,
      background: '#fff',
      borderRadius: '10px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      padding: '24px',
      alignSelf: 'flex-start',
      position: 'sticky',
      top: '24px',
    }}>

      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '20px',
      }}>
        <div style={{
          fontSize: '14px',
          fontWeight: 700,
          color: '#1f2937',
          lineHeight: 1.4,
          flex: 1,
          marginRight: '12px',
        }}>
          {item.title}
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#9ca3af',
            cursor: 'pointer',
            fontSize: '18px',
            flexShrink: 0,
          }}
        >
          {"x"}
        </button>
      </div>

      {/* Meta rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', color: '#9ca3af' }}>Source</span>
          <span style={{ fontSize: '12px', fontWeight: 500, color: '#1f2937' }}>
            {SOURCE_LABELS[item.source] || item.source}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', color: '#9ca3af' }}>Category</span>
          <span style={{ fontSize: '12px', fontWeight: 500, color: '#1f2937' }}>
            {item.category || '—'}
          </span>
        </div>

        {item.current_price && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', color: '#9ca3af' }}>Price</span>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#059669' }}>
              {'£'}{item.current_price}
              {item.price_change_pct !== null && item.price_change_pct !== 0 && (
                <span style={{
                  marginLeft: '6px',
                  fontSize: '11px',
                  color: item.price_change_pct < 0 ? '#ef4444' : '#059669',
                }}>
                  {item.price_change_pct < 0 ? '▼' : '▲'}
                  {Math.abs(item.price_change_pct).toFixed(1)}{'%'}
                </span>
              )}
            </span>
          </div>
        )}

        {item.extra_data?.author && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', color: '#9ca3af' }}>Author</span>
            <span style={{ fontSize: '12px', fontWeight: 500, color: '#1f2937' }}>
              {item.extra_data.author}
            </span>
          </div>
        )}

        {item.extra_data?.rating && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', color: '#9ca3af' }}>Rating</span>
            <span style={{ fontSize: '12px', color: '#f59e0b' }}>
              {'★'.repeat(item.extra_data.rating)}
              {'☆'.repeat(5 - item.extra_data.rating)}
            </span>
          </div>
        )}

        {item.extra_data?.tags?.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '12px', color: '#9ca3af' }}>Tags</span>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '4px',
              justifyContent: 'flex-end',
              maxWidth: '220px',
            }}>
              {item.extra_data.tags.slice(0, 5).map(tag => (
                <span key={tag} style={{
                  background: '#f3f4f6',
                  color: '#6b7280',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '11px',
                }}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', color: '#9ca3af' }}>First seen</span>
          <span style={{ fontSize: '12px', color: '#6b7280' }}>{timeAgo(item.first_seen_at)}</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', color: '#9ca3af' }}>Last scraped</span>
          <span style={{ fontSize: '12px', color: '#6b7280' }}>{timeAgo(item.last_scraped_at)}</span>
        </div>

      </div>

      {/* View original link */}
      
        <a href={item.url}
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'block',
          textAlign: 'center',
          padding: '8px',
          borderRadius: '8px',
          border: '1px solid #e5e7eb',
          fontSize: '13px',
          color: '#6366f1',
          textDecoration: 'none',
          marginBottom: '20px',
        }}
      >
        {"View original"}
      </a>

      {/* Price chart */}
      {item.current_price && (
        <div>
          <div style={{
            fontSize: '12px',
            fontWeight: 600,
            color: '#6b7280',
            marginBottom: '12px',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            Price History
          </div>
          {loading ? (
            <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: '13px', padding: '20px' }}>
              Loading chart...
            </div>
          ) : chartData.length < 2 ? (
            <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: '13px', padding: '20px' }}>
              Need more scrape runs to show trend
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#9ca3af' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => `£${v}`}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  formatter={v => [`£${v}`, 'Price']}
                  contentStyle={{
                    borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                    fontSize: '12px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={{ fill: '#6366f1', r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

    </div>
  )
}

export default function Items() {
  const [items, setItems]           = useState([])
  const [total, setTotal]           = useState(0)
  const [page, setPage]             = useState(1)
  const [search, setSearch]         = useState('')
  const [source, setSource]         = useState('')
  const [loading, setLoading]       = useState(true)
  const [selected, setSelected]     = useState(null)
  const [alertedIds, setAlertedIds] = useState(new Set())

  const pageSize = 25

  useEffect(() => {
    getAlerts()
      .then(res => setAlertedIds(new Set(res.data.map(a => a.item_id))))
      .catch(console.error)
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = { page, page_size: pageSize }
    if (search) params.search = search
    if (source) params.source = source

    getItems(params)
      .then(res => {
        setItems(res.data.items)
        setTotal(res.data.total)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [page, search, source])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div style={{ padding: '32px' }}>

      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1f2937' }}>
          Items
        </h1>
        <p style={{ color: '#6b7280', marginTop: '4px' }}>
          {total} items tracked across all sources
        </p>
      </div>

      <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>

        {/* Left — table */}
        <div style={{ flex: 1, minWidth: 0 }}>

          {/* Toolbar */}
          <div style={{
            background: '#fff',
            borderRadius: '10px 10px 0 0',
            padding: '14px 16px',
            borderBottom: '1px solid #f3f4f6',
            display: 'flex',
            gap: '10px',
            flexWrap: 'wrap',
            alignItems: 'center',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}>
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              style={{
                padding: '7px 12px',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                fontSize: '13px',
                width: '200px',
                outline: 'none',
              }}
            />
            <select
              value={source}
              onChange={e => { setSource(e.target.value); setPage(1) }}
              style={{
                padding: '7px 12px',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                fontSize: '13px',
                outline: 'none',
                background: '#fff',
                cursor: 'pointer',
              }}
            >
              <option value="">All Sources</option>
              <option value="books_toscrape">Books</option>
              <option value="quotes_toscrape">Quotes</option>
            </select>
            <span style={{ marginLeft: 'auto', fontSize: '13px', color: '#9ca3af' }}>
              Page {page} of {totalPages}
            </span>
          </div>

          {/* Table */}
          <div style={{
            background: '#fff',
            borderRadius: '0 0 10px 10px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            overflow: 'hidden',
          }}>
            {loading ? (
              <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
                Loading...
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {['Title', 'Source', 'Category', 'Price', 'Last Scraped'].map(h => (
                      <th key={h} style={{
                        padding: '10px 14px',
                        textAlign: 'left',
                        fontSize: '11px',
                        fontWeight: 600,
                        color: '#6b7280',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        borderBottom: '1px solid #f3f4f6',
                        whiteSpace: 'nowrap',
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, i) => (
                    <tr
                      key={item.id}
                      onClick={() => setSelected(item)}
                      style={{
                        background: selected?.id === item.id
                          ? '#eef2ff'
                          : i % 2 === 0 ? '#fff' : '#fafafa',
                        cursor: 'pointer',
                        borderLeft: selected?.id === item.id
                          ? '3px solid #6366f1'
                          : '3px solid transparent',
                      }}
                      onMouseEnter={e => {
                        if (selected?.id !== item.id)
                          e.currentTarget.style.background = '#f5f7ff'
                      }}
                      onMouseLeave={e => {
                        if (selected?.id !== item.id)
                          e.currentTarget.style.background = i % 2 === 0 ? '#fff' : '#fafafa'
                      }}
                    >
                      <td style={{ padding: '10px 14px', fontSize: '13px', color: '#1f2937', maxWidth: '240px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {alertedIds.has(item.id) && (
                            <span title="Alert active" style={{ fontSize: '12px', flexShrink: 0 }}>
                              {'🔔'}
                            </span>
                          )}
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.title}
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          background: item.source === 'books_toscrape' ? '#ede9fe' : '#d1fae5',
                          color: item.source === 'books_toscrape' ? '#7c3aed' : '#059669',
                          borderRadius: '20px',
                          padding: '2px 8px',
                          fontSize: '11px',
                          fontWeight: 500,
                        }}>
                          {SOURCE_LABELS[item.source] || item.source}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', fontSize: '12px', color: '#6b7280' }}>
                        {item.category || '—'}
                      </td>
                      <td style={{ padding: '10px 14px', fontSize: '13px', fontWeight: 600, color: '#059669' }}>
                        {item.current_price ? `£${item.current_price}` : '—'}
                      </td>
                      <td style={{ padding: '10px 14px', fontSize: '12px', color: '#9ca3af' }}>
                        {timeAgo(item.last_scraped_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {/* Pagination */}
            <div style={{
              padding: '12px 16px',
              borderTop: '1px solid #f3f4f6',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  border: '1px solid #e5e7eb',
                  background: '#fff',
                  cursor: page === 1 ? 'not-allowed' : 'pointer',
                  opacity: page === 1 ? 0.4 : 1,
                  fontSize: '13px',
                }}
              >
                Previous
              </button>
              <span style={{ fontSize: '13px', color: '#6b7280' }}>
                {total} total items
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  border: '1px solid #e5e7eb',
                  background: '#fff',
                  cursor: page === totalPages ? 'not-allowed' : 'pointer',
                  opacity: page === totalPages ? 0.4 : 1,
                  fontSize: '13px',
                }}
              >
                Next
              </button>
            </div>
          </div>
        </div>

        {/* Right — detail panel */}
        {selected && (
          <DetailPanel
            item={selected}
            onClose={() => setSelected(null)}
          />
        )}

      </div>
    </div>
  )
}