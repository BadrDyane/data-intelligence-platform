import { useState } from 'react'
import { triggerScrape } from '../api/client'

export default function ScrapeButton({ onComplete }) {
  const [status, setStatus] = useState('idle')
  // status: idle | loading | success | error

  const handleScrape = async () => {
    setStatus('loading')
    try {
      await triggerScrape('books_toscrape')
      setStatus('success')
      // Wait 3 seconds then reset — gives user time to read the message
      setTimeout(() => {
        setStatus('idle')
        onComplete?.()   // Tell the dashboard to refresh its data
      }, 3000)
    } catch (err) {
      console.error('Scrape error:', err)
      setStatus('error')
      setTimeout(() => setStatus('idle'), 3000)
    }
  }

  const configs = {
    idle: {
      label: 'Scrape Now',
      bg: '#6366f1',
      hover: '#4f46e5',
    },
    loading: {
      label: 'Scraping...',
      bg: '#8b5cf6',
      hover: '#8b5cf6',
    },
    success: {
      label: 'Scrape Started',
      bg: '#10b981',
      hover: '#10b981',
    },
    error: {
      label: 'Failed — Retry',
      bg: '#ef4444',
      hover: '#ef4444',
    },
  }

  const config = configs[status]

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <button
        onClick={handleScrape}
        disabled={status === 'loading'}
        style={{
          padding: '10px 20px',
          background: config.bg,
          color: '#fff',
          border: 'none',
          borderRadius: '8px',
          fontSize: '14px',
          fontWeight: 600,
          cursor: status === 'loading' ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'background 0.2s',
          opacity: status === 'loading' ? 0.85 : 1,
        }}
      >
        {status === 'loading' && (
          <span style={{
            width: '14px',
            height: '14px',
            border: '2px solid rgba(255,255,255,0.3)',
            borderTop: '2px solid #fff',
            borderRadius: '50%',
            display: 'inline-block',
            animation: 'spin 0.8s linear infinite',
          }}/>
        )}
        {config.label}
      </button>

      {status === 'success' && (
        <span style={{ fontSize: '13px', color: '#10b981' }}>
          Running in background — check Scrape Runs for progress
        </span>
      )}

      {status === 'error' && (
        <span style={{ fontSize: '13px', color: '#ef4444' }}>
          Could not reach the server
        </span>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}