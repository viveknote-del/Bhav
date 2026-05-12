'use client'

import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '@/lib/api'
import type { Exchange, Instrument, InstrumentList } from '@/types'

const PAGE_SIZE = 50

export default function InstrumentsPage() {
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [exchange, setExchange] = useState<Exchange | ''>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    apiClient
      .get<InstrumentList>('/v1/instruments', {
        params: {
          page,
          limit: PAGE_SIZE,
          search: search || undefined,
          exchange: exchange || undefined,
        },
      })
      .then((res) => {
        if (cancelled) return
        setInstruments(res.data.items)
        setTotal(res.data.total)
        setError(null)
      })
      .catch((e) => {
        if (cancelled) return
        setError(e?.message ?? 'Failed to load instruments')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, search, exchange])

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total])

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 px-6 py-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-6">
          <h1 className="text-3xl font-semibold">Instruments</h1>
          <p className="text-zinc-400 text-sm mt-1">
            NIFTY 50 universe. {total} symbols.
          </p>
        </header>

        <div className="flex gap-3 mb-6">
          <input
            type="text"
            placeholder="Search by symbol or name…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            className="flex-1 bg-zinc-900 border border-zinc-800 rounded px-3 py-2 text-sm placeholder:text-zinc-500"
          />
          <select
            value={exchange}
            onChange={(e) => {
              setExchange(e.target.value as Exchange | '')
              setPage(1)
            }}
            className="bg-zinc-900 border border-zinc-800 rounded px-3 py-2 text-sm"
          >
            <option value="">All exchanges</option>
            <option value="NSE">NSE</option>
            <option value="BSE">BSE</option>
          </select>
        </div>

        {error && (
          <div className="bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-zinc-500 text-sm">Loading…</div>
        ) : instruments.length === 0 ? (
          <div className="text-zinc-500 text-sm">
            No instruments. Run <code className="bg-zinc-900 px-1.5 py-0.5 rounded">make seed</code> to load the NIFTY 50 universe.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-zinc-400 border-b border-zinc-800">
              <tr>
                <th className="text-left py-2 px-2">Symbol</th>
                <th className="text-left py-2 px-2">Name</th>
                <th className="text-left py-2 px-2">Sector</th>
                <th className="text-right py-2 px-2">Market Cap</th>
              </tr>
            </thead>
            <tbody>
              {instruments.map((i) => (
                <tr
                  key={i.symbol}
                  className="border-b border-zinc-900 hover:bg-zinc-900/50"
                >
                  <td className="py-2 px-2 font-mono text-zinc-300">{i.symbol}</td>
                  <td className="py-2 px-2">{i.name}</td>
                  <td className="py-2 px-2 text-zinc-400">{i.sector ?? '—'}</td>
                  <td className="py-2 px-2 text-right text-zinc-400 tabular-nums">
                    {formatCap(i.market_cap)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between text-sm">
            <span className="text-zinc-500">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded border border-zinc-800 disabled:opacity-40 hover:bg-zinc-900"
              >
                Prev
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1 rounded border border-zinc-800 disabled:opacity-40 hover:bg-zinc-900"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

function formatCap(cap: number | null): string {
  if (cap === null) return '—'
  if (cap >= 1e12) return `₹${(cap / 1e12).toFixed(2)} T`
  if (cap >= 1e9) return `₹${(cap / 1e9).toFixed(2)} B`
  if (cap >= 1e6) return `₹${(cap / 1e6).toFixed(2)} M`
  return `₹${cap.toFixed(0)}`
}
