import { useState } from 'react'
import { createAlert } from '../api/client'

export default function AlertModal({ item, onClose, onCreated }) {
  const [condition, setCondition] = useState('price_below')
  const [threshold, setThreshold] = useState('')
  const [email, setEmail]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)

  const handleSubmit = async () => {
    if (!threshold) {
      setError('Please enter a threshold price')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await createAlert({
        item_id:      item.id,
        condition,
        threshold:    parseFloat(threshold),
        notify_email: email || null,
        label:        `${condition} £${threshold} — ${item.title}`,
      })
      onCreated?.()
      onClose()
    } catch (err) {
      setError('Failed to create alert. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.4)',
          zIndex: 100,
        }}
      />

      {/* Modal */}
      <div style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: '#fff',
        borderRadius: '14px',
        padding: '28px',
        width: '420px',
        zIndex: 101,
        boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
      }}>

        {/* Header */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#1f2937' }}>
            Create Price Alert
          </div>
          <div style={{
            fontSize: '12px',
            color: '#6b7280',
            marginTop: '4px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {item.title}
          </div>
        </div>

        {/* Current price info */}
        <div style={{
          background: '#f9fafb',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: '13px', color: '#6b7280' }}>Current price</span>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#1f2937' }}>
            £{item.current_price}
          </span>
        </div>

        {/* Condition */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '6px' }}>
            Alert condition
          </label>
          <select
            value={condition}
            onChange={e => setCondition(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 12px',
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '13px',
              background: '#fff',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="price_below">Price drops below threshold</option>
            <option value="price_above">Price rises above threshold</option>
            <option value="price_drop">Price drops by % or more</option>
          </select>
        </div>

        {/* Threshold */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '6px' }}>
            {condition === 'price_drop' ? 'Drop percentage (%)' : 'Threshold price (£)'}
          </label>
          <input
            type="number"
            placeholder={condition === 'price_drop' ? 'e.g. 10' : 'e.g. 30.00'}
            value={threshold}
            onChange={e => setThreshold(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 12px',
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '13px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Email */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '6px' }}>
            Notify email <span style={{ color: '#9ca3af', fontWeight: 400 }}>(optional)</span>
          </label>
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 12px',
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '13px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: '#fee2e2',
            color: '#ef4444',
            borderRadius: '8px',
            padding: '10px 14px',
            fontSize: '13px',
            marginBottom: '16px',
          }}>
            {error}
          </div>
        )}

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              background: '#fff',
              fontSize: '14px',
              cursor: 'pointer',
              color: '#374151',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              border: 'none',
              background: '#6366f1',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.8 : 1,
            }}
          >
            {loading ? 'Creating...' : 'Create Alert'}
          </button>
        </div>
      </div>
    </>
  )
}