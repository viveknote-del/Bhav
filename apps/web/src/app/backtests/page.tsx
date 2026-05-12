'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api'

interface DetectorSummary {
  detector: string
  n_signals: number
  hit_rate: number
  win_rate: number
  mean_forward_return: number
  mean_composite_score: number
}

interface BacktestResult {
  start: string
  end: string
  forward_window_days: number
  win_threshold: number
  universe_size: number
  summaries: DetectorSummary[]
}

function isoOffset(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

export default function BacktestPage() {
  const [start, setStart] = useState(isoOffset(-180))
  const [end, setEnd] = useState(isoOffset(-1))
  const [forward, setForward] = useState(20)
  const [win, setWin] = useState(0.05)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await apiClient.post<BacktestResult>('/v1/backtests', {
        start,
        end,
        forward_window_days: forward,
        win_threshold: win,
      })
      setResult(r.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Backtest failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <header className="mb-6">
          <h1 className="text-3xl font-semibold tracking-tight">Backtest detectors</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Replays every detector against the cached daily_bars. Only signals
            with enough forward bars to compute a return are counted.
          </p>
        </header>

        <section className="bg-zinc-900/40 border border-zinc-900 rounded-lg p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <label className="text-xs text-zinc-500 flex flex-col gap-1">
              Start
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-sm text-zinc-100"
              />
            </label>
            <label className="text-xs text-zinc-500 flex flex-col gap-1">
              End
              <input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-sm text-zinc-100"
              />
            </label>
            <label className="text-xs text-zinc-500 flex flex-col gap-1">
              Forward (days)
              <input
                type="number"
                min={1}
                max={120}
                value={forward}
                onChange={(e) => setForward(Number(e.target.value))}
                className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-sm text-zinc-100 tabular-nums"
              />
            </label>
            <label className="text-xs text-zinc-500 flex flex-col gap-1">
              Win threshold (e.g. 0.05 = 5%)
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={win}
                onChange={(e) => setWin(Number(e.target.value))}
                className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-sm text-zinc-100 tabular-nums"
              />
            </label>
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="mt-4 px-4 py-1.5 rounded text-sm bg-zinc-100 text-zinc-950 hover:bg-zinc-200 disabled:opacity-40"
          >
            {loading ? 'Running…' : 'Run backtest'}
          </button>
          <p className="mt-2 text-xs text-zinc-500">
            Tip: daily_bars must be populated. A few completed scans cover the universe.
          </p>
        </section>

        {error && (
          <div className="bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        {result && (
          <section>
            <p className="text-sm text-zinc-500 mb-3">
              {result.universe_size} symbols · {result.start} → {result.end} ·
              forward {result.forward_window_days}d · win ≥ {(result.win_threshold * 100).toFixed(1)}%
            </p>
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wider text-zinc-500 border-b border-zinc-900">
                <tr>
                  <th className="text-left py-2 px-2">Detector</th>
                  <th className="text-right py-2 px-2">Signals</th>
                  <th className="text-right py-2 px-2">Hit %</th>
                  <th className="text-right py-2 px-2">Win %</th>
                  <th className="text-right py-2 px-2">Mean fwd</th>
                  <th className="text-right py-2 px-2">Mean score</th>
                </tr>
              </thead>
              <tbody>
                {result.summaries.map((s) => (
                  <tr key={s.detector} className="border-b border-zinc-900">
                    <td className="py-2 px-2 font-mono text-zinc-300">{s.detector}</td>
                    <td className="py-2 px-2 text-right tabular-nums">{s.n_signals}</td>
                    <td className="py-2 px-2 text-right tabular-nums">{(s.hit_rate * 100).toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right tabular-nums">{(s.win_rate * 100).toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right tabular-nums">{(s.mean_forward_return * 100).toFixed(2)}%</td>
                    <td className="py-2 px-2 text-right tabular-nums">{s.mean_composite_score.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {result.summaries.every((s) => s.n_signals === 0) && (
              <p className="mt-4 text-sm text-zinc-500">
                Zero signals across all detectors. Either the date range is too short, daily_bars
                aren't populated for those dates, or the universe lacks history.
              </p>
            )}
          </section>
        )}
      </div>
    </main>
  )
}
