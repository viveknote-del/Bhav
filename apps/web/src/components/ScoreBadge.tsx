import { clsx } from 'clsx'

export function ScoreBadge({ score }: { score: number }) {
  const tier =
    score >= 75 ? 'high' : score >= 55 ? 'mid' : 'low'
  return (
    <span
      className={clsx(
        'inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-semibold tabular-nums min-w-[2.5rem]',
        tier === 'high' && 'bg-emerald-950/60 text-emerald-300 border border-emerald-900',
        tier === 'mid' && 'bg-amber-950/60 text-amber-300 border border-amber-900',
        tier === 'low' && 'bg-zinc-900 text-zinc-400 border border-zinc-800',
      )}
    >
      {Math.round(score)}
    </span>
  )
}
