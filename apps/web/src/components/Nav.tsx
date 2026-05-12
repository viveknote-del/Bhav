'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { clsx } from 'clsx'

const LINKS = [
  { href: '/', label: 'Today' },
  { href: '/scans', label: 'Scans' },
  { href: '/instruments', label: 'Instruments' },
  { href: '/watchlist', label: 'Watchlist' },
  { href: '/backtests', label: 'Backtest' },
]

export function Nav() {
  const pathname = usePathname()
  return (
    <nav className="border-b border-zinc-900 bg-zinc-950">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-6">
        <Link href="/" className="text-zinc-100 font-semibold tracking-tight">
          Bhav
        </Link>
        <div className="flex gap-1 text-sm">
          {LINKS.map((l) => {
            const active = l.href === '/' ? pathname === '/' : pathname.startsWith(l.href)
            return (
              <Link
                key={l.href}
                href={l.href}
                className={clsx(
                  'px-3 py-1.5 rounded transition-colors',
                  active
                    ? 'bg-zinc-900 text-zinc-100'
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/50',
                )}
              >
                {l.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
