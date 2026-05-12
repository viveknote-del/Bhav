import Link from 'next/link'
import type { Breakout } from '@/types'
import { ScoreBadge } from './ScoreBadge'

const TYPE_LABEL: Record<Breakout['breakout_type'], string> = {
  FIFTY_TWO_WEEK_HIGH: '52W high',
  CONSOLIDATION: 'Consolidation',
  VOLUME_SPIKE: 'Volume spike',
  PATTERN: 'Pattern',
}

function formatPrice(p: number): string {
  return `₹${p.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
}

export function BreakoutCard({ breakout }: { breakout: Breakout }) {
  const subtype = breakout.pattern_subtype ? ` · ${breakout.pattern_subtype}` : ''
  return (
    <Link
      href={`/breakouts/${breakout.id}`}
      className="block bg-zinc-950 border border-zinc-900 hover:border-zinc-700 rounded-lg p-4 transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-zinc-100">{breakout.symbol}</span>
            <ScoreBadge score={breakout.composite_score} />
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">
            {TYPE_LABEL[breakout.breakout_type]}{subtype}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-zinc-100 tabular-nums">{formatPrice(breakout.price)}</div>
          {breakout.volume_ratio != null && (
            <div className="text-xs text-zinc-500 tabular-nums">
              {breakout.volume_ratio.toFixed(1)}× vol
            </div>
          )}
        </div>
      </div>
      {breakout.ai_commentary && (
        <p className="mt-3 text-sm text-zinc-400 line-clamp-2">
          {breakout.ai_commentary}
        </p>
      )}
    </Link>
  )
}
