import { useState, useEffect } from 'react'
import { getItems } from '../api/client'

const CATEGORIES = [
  'All', 'Mystery', 'Historical Fiction', 'Sequential Art',
  'Classics', 'Philosophy', 'Romance', 'Womens Fiction',
  'Fiction', 'Childrens',
]

export default function DataTable({ onSelectItem }) {
  const [items, setItems]       = useState([])
  const [total, setTotal]       = useState(0)
  const [page, setPage]         = useState(1)
  const [search, setSearch]     = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading]   = useState(true)

  const pageSize = 20

  useEffect(() => {
    setLoading(true)
    const params = { page, page_size: pageSize }
    if (search)   params.search   = search
    if (category && category !== 'All') params.category = category

    getItems(params)
      .then(res => {
        setItems(res.data.items)
        setTotal(res.data.total)
      })
      .catch(err => console.error('Items error:', err))
      .finally(() => setLoading(false))
  }, [page, search, category])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div style={{
      background: '#fff',
      borderRadius: '10px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      overflow: 'hidden',
    }}>

      {/* Toolbar */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #f3f4f6',
        display: 'flex',
        gap: '12px',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        <input
          type="text"
          placeholder="Search titles..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          style={{
            padding: '8px 12px',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            fontSize: '13px',
            width: '220px',
            outline: 'none',
          }}
        />
        <select
          value={category}
          onChange={e => { setCategory(e.target.value); setPage(1) }}
          style={{
            padding: '8px 12px',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            fontSize: '13px',
            outline: 'none',
            background: '#fff',
            cursor: 'pointer',
          }}
        >
          {CATEGORIES.map(c => (
            <option key={c} value={c === 'All' ? '' : c}>{c}</option>
          ))}
        </select>
        <span style={{ marginLeft: 'auto', fontSize: '13px', color: '#9ca3af' }}>
          {total} items
        </span>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
          Loading...
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f9fafb' }}>
              {['Title', 'Category', 'Price', 'Rating', 'Available'].map(h => (
                <th key={h} style={{
                  padding: '12px 16px',
                  textAlign: 'left',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: '#6b7280',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  borderBottom: '1px solid #f3f4f6',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr
                key={item.id}
                onClick={() => onSelectItem?.(item)}
                style={{
                  background: i % 2 === 0 ? '#fff' : '#fafafa',
                  cursor: 'pointer',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#eef2ff'}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? '#fff' : '#fafafa'}
              >
                <td style={{ padding: '12px 16px', fontSize: '13px', color: '#1f2937', maxWidth: '280px' }}>
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.title}
                  </div>
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    background: '#eef2ff',
                    color: '#4f46e5',
                    borderRadius: '20px',
                    padding: '2px 10px',
                    fontSize: '12px',
                    fontWeight: 500,
                  }}>
                    {item.category || 'General'}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '13px', fontWeight: 600, color: '#059669' }}>
                  £{item.current_price}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '13px', color: '#6b7280' }}>
                  {'★'.repeat(item.extra_data?.rating || 0)}{'☆'.repeat(5 - (item.extra_data?.rating || 0))}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    color: item.is_available ? '#10b981' : '#ef4444',
                    fontSize: '12px',
                    fontWeight: 500,
                  }}>
                    {item.is_available ? 'In Stock' : 'Out of Stock'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Pagination */}
      <div style={{
        padding: '14px 20px',
        borderTop: '1px solid #f3f4f6',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
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
          Page {page} of {totalPages}
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
  )
}