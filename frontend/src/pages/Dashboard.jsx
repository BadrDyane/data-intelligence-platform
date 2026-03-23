import { useState, useCallback } from 'react'
import SummaryCards from '../components/SummaryCards'
import DataTable from '../components/DataTable'
import PriceChart from '../components/PriceChart'
import ScrapeButton from '../components/ScrapeButton'
import AlertModal from '../components/AlertModal'

export default function Dashboard() {
  const [selectedItem, setSelectedItem] = useState(null)
  const [alertItem, setAlertItem]       = useState(null)
  const [refreshKey, setRefreshKey]     = useState(0)

  const handleScrapeComplete = useCallback(() => {
    setRefreshKey(k => k + 1)
  }, [])

  const handleAlertCreated = useCallback(() => {
    setRefreshKey(k => k + 1)
  }, [])

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
            Dashboard
          </h1>
          <p style={{ color: '#6b7280', marginTop: '4px' }}>
            Live market intelligence — books.toscrape.com
          </p>
        </div>
        <ScrapeButton onComplete={handleScrapeComplete} />
      </div>

      {/* Summary cards */}
      <SummaryCards key={refreshKey} />

      <div style={{ marginTop: '32px' }} />

      {/* Price chart */}
      <PriceChart item={selectedItem} />

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
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              onClick={() => setAlertItem(selectedItem)}
              style={{
                padding: '6px 14px',
                background: '#6366f1',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Set Alert
            </button>
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
        </div>
      )}

      {/* Data table */}
      <DataTable onSelectItem={setSelectedItem} />

      {/* Alert modal */}
      {alertItem && (
        <AlertModal
          item={alertItem}
          onClose={() => setAlertItem(null)}
          onCreated={handleAlertCreated}
        />
      )}

    </div>
  )
}