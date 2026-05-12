import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-950 text-zinc-100">
      <div className="text-center px-6">
        <h1 className="text-5xl font-bold tracking-tight">Bhav</h1>
        <p className="mt-3 text-zinc-400">Indian stock breakout screener</p>
        <p className="mt-8 text-sm text-zinc-500">
          No scans yet. The scanner will run automatically after market close (15:35 IST).
        </p>
        <Link
          href="/instruments"
          className="mt-6 inline-block px-4 py-2 rounded border border-zinc-700 text-sm hover:bg-zinc-900"
        >
          Browse instruments →
        </Link>
      </div>
    </main>
  )
}
