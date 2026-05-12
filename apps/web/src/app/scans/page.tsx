'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'
import type { ScanRunList } from '@/types'

export default function ScansPage() {
  const [scans, setScans] = useState<ScanRunList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)

  const load = async () => {
    try {
      const r = await apiClient.get<ScanRunList>('/v1/scans', { params: { limit: 50 } })
      setScans(r.data)
      setError(null)
    } catch (e) {
      setError((e as Error).message ?? 'Failed to load scans')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const trigger = async () => {
    setTriggering(true)
    try {
      await apiClient.post('/v1/scans', { scan_type: 'EOD' })
      await load()
    } catch (e) {
      setError((e as Error).message ?? 'Trigger failed')
    } finally {
      setTriggering(false)
    }
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Scan history</h1>
            <p className="text-sm text-zinc-500 mt-1">
              Each scan runs detectors over the active universe and persists ranked breakouts.
            </p>
          </div>
          <button
            onClick={trigger}
            disabled={triggering}
            className="px-3 py-1.5 rounded border border-zinc-800 text-sm hover:bg-zinc-900 disabled:opacity-40"
          >
            {triggering ? 'Triggering…' : 'Run scan now'}
          </button>
        </header>

        {error && (
          <div className="bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-zinc-500 text-sm">Loading…</p>
        ) : !scans || scans.items.length === 0 ? (
          <p className="text-zinc-500 text-sm">No scans yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-zinc-500 text-xs uppercase tracking-wider border-b border-zinc-900">
              <tr>
                <th className="text-left py-2 px-2">Started</th>
                <th className="text-left py-2 px-2">Type</th>
                <th className="text-left py-2 px-2">Status</th>
                <th className="text-right py-2 px-2">Universe</th>
                <th className="text-right py-2 px-2">Breakouts</th>
                <th className="text-right py-2 px-2">Duration</th>
              </tr>
            </thead>
            <tbody>
              {scans.items.map((s) => {
                const duration =
                  s.finished_at && s.started_at
                    ? Math.round(
                        (new Date(s.finished_at).getTime() -
                          new Date(s.started_at).getTime()) /
                          1000,
                      )
                    : null
                return (
                  <tr key={s.id} className="border-b border-zinc-900">
                    <td className="py-2 px-2 text-zinc-300">
                      {new Date(s.started_at).toLocaleString('en-IN', {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}
                    </td>
                    <td className="py-2 px-2 text-zinc-400">{s.scan_type}</td>
                    <td className="py-2 px-2">
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="py-2 px-2 text-right text-zinc-400 tabular-nums">
                      {s.universe_size ?? '—'}
                    </td>
                    <td className="py-2 px-2 text-right text-zinc-200 tabular-nums">
                      {s.breakouts_found ?? '—'}
                    </td>
                    <td className="py-2 px-2 text-right text-zinc-500 tabular-nums">
                      {duration != null ? `${duration}s` : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </main>
  )
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'COMPLETED'
      ? 'bg-emerald-950/60 text-emerald-300 border-emerald-900'
      : status === 'RUNNING'
        ? 'bg-amber-950/60 text-amber-300 border-amber-900'
        : 'bg-red-950/60 text-red-300 border-red-900'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs border ${cls}`}>
      {status.toLowerCase()}
    </span>
  )
}
