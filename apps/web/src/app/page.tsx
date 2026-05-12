'use client'

import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '@/lib/api'
import type { Breakout, BreakoutType, ScanDetail, ScanRunList } from '@/types'
import { BreakoutCard } from '@/components/BreakoutCard'
import { BreakoutFilters } from '@/components/BreakoutFilters'

export default function Home() {
  const [latest, setLatest] = useState<ScanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [type, setType] = useState<BreakoutType | null>(null)
  const [minScore, setMinScore] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const list = await apiClient.get<ScanRunList>('/v1/scans', { params: { limit: 1 } })
        const runs = list.data.items
        if (runs.length === 0) {
          if (!cancelled) {
            setLatest(null)
            setError(null)
          }
          return
        }
        const detail = await apiClient.get<ScanDetail>(`/v1/scans/${runs[0].id}`)
        if (!cancelled) {
          setLatest(detail.data)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message ?? 'Failed to load')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const filtered = useMemo<Breakout[]>(() => {
    if (!latest) return []
    return latest.breakouts.filter((b) => {
      if (type && b.breakout_type !== type) return false
      if (b.composite_score < minScore) return false
      return true
    })
  }, [latest, type, minScore])

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <header className="mb-6">
          <h1 className="text-3xl font-semibold tracking-tight">Today's breakouts</h1>
          {latest && (
            <p className="text-sm text-zinc-500 mt-1">
              Scan {latest.scan.id.slice(0, 8)} · {latest.scan.status.toLowerCase()} ·
              {' '}{latest.scan.breakouts_found ?? '—'} signals over{' '}
              {latest.scan.universe_size ?? '—'} symbols
            </p>
          )}
        </header>

        {error && (
          <div className="bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-zinc-500 text-sm">Loading…</p>
        ) : !latest ? (
          <EmptyState />
        ) : (
          <>
            {latest.scan.summary && (
              <section className="mb-6 bg-zinc-900/40 border border-zinc-900 rounded-lg p-5">
                <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">
                  EOD digest
                </h2>
                <p className="text-zinc-200 leading-relaxed">{latest.scan.summary}</p>
              </section>
            )}

            <BreakoutFilters
              type={type}
              setType={setType}
              minScore={minScore}
              setMinScore={setMinScore}
            />

            {filtered.length === 0 ? (
              <p className="text-zinc-500 text-sm">No breakouts match the current filters.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {filtered.map((b) => (
                  <BreakoutCard key={b.id} breakout={b} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}

function EmptyState() {
  return (
    <div className="text-zinc-500 text-sm space-y-2">
      <p>No scans yet. To run one:</p>
      <pre className="mt-3 bg-zinc-900 text-zinc-300 px-4 py-3 rounded text-xs overflow-x-auto">
{`# In separate terminals
make api          # FastAPI
make worker       # arq worker (runs scans + commentary)
make scan-now     # trigger a scan`}
      </pre>
      <p className="mt-3">The scanner also runs automatically at 15:35 IST after market close.</p>
    </div>
  )
}
