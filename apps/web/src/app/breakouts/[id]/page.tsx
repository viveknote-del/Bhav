'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { apiClient } from '@/lib/api'
import type { Breakout, Chart } from '@/types'
import { PriceChart } from '@/components/PriceChart'
import { ScoreBadge } from '@/components/ScoreBadge'

const TYPE_LABEL: Record<Breakout['breakout_type'], string> = {
  FIFTY_TWO_WEEK_HIGH: '52-week high',
  CONSOLIDATION: 'Consolidation',
  VOLUME_SPIKE: 'Volume spike',
  PATTERN: 'Pattern',
}

export default function BreakoutDetailPage({ params }: { params: { id: string } }) {
  const [breakout, setBreakout] = useState<Breakout | null>(null)
  const [chart, setChart] = useState<Chart | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [regenLoading, setRegenLoading] = useState(false)
  const [inWatchlist, setInWatchlist] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const b = await apiClient.get<Breakout>(`/v1/breakouts/${params.id}`)
        if (cancelled) return
        setBreakout(b.data)
        const c = await apiClient.get<Chart>(`/v1/charts/${b.data.symbol}`, { params: { days: 180 } })
        if (cancelled) return
        setChart(c.data)
      } catch (e) {
        if (!cancelled) setError((e as Error).message ?? 'Failed to load')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [params.id])

  useEffect(() => {
    if (!breakout) return
    apiClient.get('/v1/watchlist').then((res) => {
      const items = res.data as { symbol: string }[]
      setInWatchlist(items.some((i) => i.symbol === breakout.symbol))
    }).catch(() => setInWatchlist(null))
  }, [breakout])

  const toggleWatchlist = async () => {
    if (!breakout || inWatchlist === null) return
    try {
      if (inWatchlist) {
        await apiClient.delete(`/v1/watchlist/${breakout.symbol}`)
      } else {
        await apiClient.post('/v1/watchlist', { symbol: breakout.symbol })
      }
      setInWatchlist((s) => !s)
    } catch (e) {
      setError((e as Error).message ?? 'Watchlist update failed')
    }
  }

  const regenerate = async () => {
    if (!breakout) return
    setRegenLoading(true)
    try {
      const r = await apiClient.post<Breakout>(`/v1/breakouts/${breakout.id}/commentary`)
      setBreakout(r.data)
    } catch (e) {
      setError((e as Error).message ?? 'Regen failed')
    } finally {
      setRegenLoading(false)
    }
  }

  if (loading) {
    return <Shell><p className="text-zinc-500 text-sm">Loading…</p></Shell>
  }
  if (error || !breakout) {
    return (
      <Shell>
        <p className="text-red-300 text-sm">{error ?? 'Breakout not found'}</p>
        <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-100">← back</Link>
      </Shell>
    )
  }

  const indicators = breakout.indicators ?? {}
  const breakoutDate = breakout.detected_at?.slice(0, 10)

  return (
    <Shell>
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-100">← Today's breakouts</Link>

      <header className="mt-4 mb-6 flex flex-wrap items-start gap-4 justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight font-mono">{breakout.symbol}</h1>
            <ScoreBadge score={breakout.composite_score} />
          </div>
          <p className="text-sm text-zinc-500 mt-1">
            {TYPE_LABEL[breakout.breakout_type]}
            {breakout.pattern_subtype ? ` · ${breakout.pattern_subtype}` : ''}
            {' · detected '}
            {new Date(breakout.detected_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={toggleWatchlist}
            disabled={inWatchlist === null}
            className="px-3 py-1.5 rounded border border-zinc-800 text-sm hover:bg-zinc-900 disabled:opacity-40"
          >
            {inWatchlist === null ? '...' : inWatchlist ? '★ Watching' : '☆ Watch'}
          </button>
          <button
            onClick={regenerate}
            disabled={regenLoading}
            className="px-3 py-1.5 rounded border border-zinc-800 text-sm hover:bg-zinc-900 disabled:opacity-40"
          >
            {regenLoading ? 'Generating…' : 'Regenerate commentary'}
          </button>
        </div>
      </header>

      <section className="bg-zinc-950 border border-zinc-900 rounded-lg p-4 mb-6">
        {chart && chart.bars.length > 0 ? (
          <PriceChart
            bars={chart.bars}
            breakoutLevel={breakout.breakout_level}
            breakoutDate={breakoutDate}
          />
        ) : (
          <p className="text-zinc-500 text-sm">No chart data available.</p>
        )}
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Stat label="Price" value={`₹${breakout.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`} />
        <Stat
          label="Break level"
          value={breakout.breakout_level != null ? `₹${breakout.breakout_level.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '—'}
        />
        <Stat label="Volume ratio" value={breakout.volume_ratio != null ? `${breakout.volume_ratio.toFixed(2)}×` : '—'} />
        <Stat label="Composite score" value={`${Math.round(breakout.composite_score)}/100`} />
      </section>

      {Object.keys(indicators).length > 0 && (
        <section className="mb-6">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Indicators</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
            {Object.entries(indicators).map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-zinc-900 py-1">
                <span className="text-zinc-400">{k}</span>
                <span className="text-zinc-200 tabular-nums">{formatIndicator(v)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mb-6">
        <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Commentary</h2>
        {breakout.ai_commentary ? (
          <p className="text-zinc-200 leading-relaxed">{breakout.ai_commentary}</p>
        ) : (
          <p className="text-zinc-500 text-sm italic">
            Not yet generated. Top {/* settings.commentary_top_n */}20 breakouts receive AI commentary;
            this one is outside the top tier or the worker hasn't run yet.
          </p>
        )}
      </section>

      {breakout.news_links && breakout.news_links.length > 0 && (
        <section>
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Recent news</h2>
          <ul className="space-y-2 text-sm">
            {breakout.news_links.map((n, i) => (
              <li key={i}>
                <a href={n.url} target="_blank" rel="noopener noreferrer"
                   className="text-zinc-200 hover:text-zinc-100 underline-offset-2 hover:underline">
                  {n.title}
                </a>
                <span className="text-zinc-500"> · {n.source}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-5xl mx-auto px-6 py-8">{children}</div>
    </main>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-900/40 border border-zinc-900 rounded p-3">
      <div className="text-xs text-zinc-500 uppercase tracking-wider">{label}</div>
      <div className="text-zinc-100 mt-1 tabular-nums">{value}</div>
    </div>
  )
}

function formatIndicator(v: unknown): string {
  if (typeof v === 'number') return v.toLocaleString('en-IN', { maximumFractionDigits: 4 })
  if (typeof v === 'boolean') return v ? 'yes' : 'no'
  return String(v)
}
