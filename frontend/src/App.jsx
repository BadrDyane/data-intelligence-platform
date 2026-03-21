import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import './App.css'

export default function App() {
  const [activePage, setActivePage] = useState('dashboard')

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>

      {/* Sidebar */}
      <aside style={{
        width: '220px',
        background: '#1a1a2e',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        padding: '0',
        flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{
          padding: '24px 20px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>
            DataIntel
          </div>
          <div style={{ fontSize: '11px', color: '#6366f1', marginTop: '2px' }}>
            Intelligence Platform
          </div>
        </div>

        {/* Nav links */}
        <nav style={{ padding: '16px 0', flex: 1 }}>
          {[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'items',     label: 'Items' },
            { id: 'runs',      label: 'Scrape Runs' },
          ].map(link => (
            <button
              key={link.id}
              onClick={() => setActivePage(link.id)}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                padding: '10px 20px',
                background: activePage === link.id
                  ? 'rgba(99,102,241,0.15)'
                  : 'transparent',
                color: activePage === link.id ? '#818cf8' : '#9ca3af',
                border: 'none',
                borderLeft: activePage === link.id
                  ? '3px solid #6366f1'
                  : '3px solid transparent',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: activePage === link.id ? 600 : 400,
                transition: 'all 0.15s',
              }}
            >
              {link.label}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div style={{
          padding: '16px 20px',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          fontSize: '11px',
          color: '#4b5563',
        }}>
          v1.0.0
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflow: 'auto' }}>
        <Dashboard />
      </main>

    </div>
  )
}