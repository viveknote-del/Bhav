'use client'

import { clsx } from 'clsx'
import type { BreakoutType } from '@/types'

const TYPES: { value: BreakoutType; label: string }[] = [
  { value: 'FIFTY_TWO_WEEK_HIGH', label: '52W high' },
  { value: 'CONSOLIDATION', label: 'Consolidation' },
  { value: 'VOLUME_SPIKE', label: 'Volume' },
  { value: 'PATTERN', label: 'Pattern' },
]

interface Props {
  type: BreakoutType | null
  setType: (t: BreakoutType | null) => void
  minScore: number
  setMinScore: (s: number) => void
}

export function BreakoutFilters({ type, setType, minScore, setMinScore }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <div className="flex gap-1.5">
        <FilterChip active={type === null} onClick={() => setType(null)}>
          All
        </FilterChip>
        {TYPES.map((t) => (
          <FilterChip
            key={t.value}
            active={type === t.value}
            onClick={() => setType(type === t.value ? null : t.value)}
          >
            {t.label}
          </FilterChip>
        ))}
      </div>
      <label className="text-xs text-zinc-500 flex items-center gap-2 ml-auto">
        Min score
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={minScore}
          onChange={(e) => setMinScore(Number(e.target.value))}
          className="accent-zinc-400"
        />
        <span className="tabular-nums text-zinc-300 w-7">{minScore}</span>
      </label>
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'px-3 py-1 rounded-full text-xs font-medium transition-colors',
        active
          ? 'bg-zinc-100 text-zinc-950'
          : 'bg-zinc-900 text-zinc-400 hover:text-zinc-100 border border-zinc-800',
      )}
    >
      {children}
    </button>
  )
}
