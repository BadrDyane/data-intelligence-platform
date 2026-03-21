import { useState } from 'react'
import SummaryCards from '../components/SummaryCards'
import DataTable from '../components/DataTable'
import PriceChart from '../components/PriceChart'

export default function Dashboard() {
  const [selectedItem, setSelectedItem] = useState(null)

  return (
    <div style={{ padding: '32px' }}>

      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1f2937' }}>
          Dashboard
        </h1>
        <p style={{ color: '#6b7280', marginTop: '4px' }}>
          Live market intelligence — books.toscrape.com
        </p>
      </div>

      {/* Summary cards */}
      <SummaryCards />

      {/* Spacer */}
      <div style={{ marginTop: '32px' }} />

      {/* Price chart */}
      <PriceChart item={selectedItem} />

      {/* Spacer */}
      <div style={{ marginTop: '24px' }} />

      {/* Selected item banner */}
      {selectedItem && (
        <div style={{
          background: '#eef2ff',
          border: '1px solid #c7d2fe',
          borderRadius: '10px',
          padding: '14px 20px',
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span style={{ fontSize: '14px', color: '#4338ca', fontWeight: 500 }}>
            Selected: {selectedItem.title}
          </span>
          <button
            onClick={() => setSelectedItem(null)}
            style={{
              background: 'none',
              border: 'none',
              color: '#6366f1',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            Clear
          </button>
        </div>
      )}

      {/* Data table */}
      <DataTable onSelectItem={setSelectedItem} />

    </div>
  )
}