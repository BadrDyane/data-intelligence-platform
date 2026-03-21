import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// ── Items ──────────────────────────────────────────────────────────────────

export const getItems = (params = {}) =>
  client.get('/items', { params })

export const getItem = (id) =>
  client.get(`/items/${id}`)

export const getItemTrend = (id) =>
  client.get(`/items/${id}/trend`)

// ── Analytics ──────────────────────────────────────────────────────────────

export const getSummary = () =>
  client.get('/analytics/summary')

export const getRuns = () =>
  client.get('/analytics/runs')

// ── Scrape ─────────────────────────────────────────────────────────────────

export const triggerScrape = (source) =>
  client.post('/scrape', { source })

export default client