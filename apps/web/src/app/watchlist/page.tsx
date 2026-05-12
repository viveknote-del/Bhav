'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'
import type { WatchlistItem } from '@/types'

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newSymbol, setNewSymbol] = useState('')
  const [newNotes, setNewNotes] = useState('')

  const load = async () => {
    try {
      const r = await apiClient.get<WatchlistItem[]>('/v1/watchlist')
      setItems(r.data)
      setError(null)
    } catch (e) {
      setError((e as Error).message ?? 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newSymbol.trim()) return
    try {
      await apiClient.post('/v1/watchlist', {
        symbol: newSymbol.trim().toUpperCase(),
        notes: newNotes.trim() || null,
      })
      setNewSymbol('')
      setNewNotes('')
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Add failed')
    }
  }

  const remove = async (symbol: string) => {
    try {
      await apiClient.delete(`/v1/watchlist/${symbol}`)
      setItems((s) => s.filter((i) => i.symbol !== symbol))
    } catch (e) {
      setError((e as Error).message ?? 'Remove failed')
    }
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <header className="mb-6">
          <h1 className="text-3xl font-semibold tracking-tight">Watchlist</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Personal list. {items.length} {items.length === 1 ? 'symbol' : 'symbols'}.
          </p>
        </header>

        <form
          onSubmit={add}
          className="mb-6 flex flex-wrap gap-2 bg-zinc-900/40 border border-zinc-900 rounded-lg p-3"
        >
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="Symbol (e.g. RELIANCE.NS)"
            className="bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-sm flex-1 min-w-[200px]"
          />
          <input
            type="text"
            value={newNotes}
            onChange={(e) => setNewNotes(e.target.value)}
            placeholder="Notes (optional)"
            className="bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-sm flex-1 min-w-[200px]"
          />
          <button
            type="submit"
            className="px-4 py-1.5 rounded border border-zinc-800 text-sm bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
          >
            Add
          </button>
        </form>

        {error && (
          <div className="bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-zinc-500 text-sm">Loading…</p>
        ) : items.length === 0 ? (
          <p className="text-zinc-500 text-sm">
            Watchlist empty. Add a symbol above or use the “Watch” button on a breakout.
          </p>
        ) : (
          <ul className="space-y-2">
            {items.map((i) => (
              <li
                key={i.symbol}
                className="flex items-start justify-between gap-3 bg-zinc-950 border border-zinc-900 rounded-lg p-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-zinc-100">{i.symbol}</span>
                    <span className="text-zinc-500 text-sm">{i.name}</span>
                  </div>
                  <div className="text-xs text-zinc-500 mt-0.5">
                    {i.sector ?? '—'} · added {new Date(i.added_at).toLocaleDateString('en-IN')}
                  </div>
                  {i.notes && <p className="mt-2 text-sm text-zinc-300">{i.notes}</p>}
                </div>
                <button
                  onClick={() => remove(i.symbol)}
                  className="px-2 py-1 text-xs text-zinc-400 hover:text-red-300 hover:bg-red-950/40 rounded"
                >
                  remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  )
}
