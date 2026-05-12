import { test, expect } from '@playwright/test'

/**
 * Happy-path smoke test.
 *
 * Prereqs (the test does NOT bootstrap these — keep CI in mind):
 *   - Postgres + Redis up (`docker compose up -d`)
 *   - API running on :8000 (`make api`)
 *   - Worker running (`make worker`)
 *   - Universe seeded (`make seed`)
 *   - At least one completed scan with breakouts
 *
 * If those preconditions aren't met, tests skip rather than fail noisily.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function hasCompletedScan(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/v1/scans?limit=1`)
    if (!r.ok) return false
    const body = (await r.json()) as { items: { status: string; breakouts_found: number | null }[] }
    return body.items.length > 0 && body.items[0].status === 'COMPLETED' && (body.items[0].breakouts_found ?? 0) > 0
  } catch {
    return false
  }
}

test.describe('scan → breakouts → detail', () => {
  test.beforeAll(async () => {
    test.skip(!(await hasCompletedScan()), 'no completed scan with breakouts in the local DB; run `make scan-now` first')
  })

  test('home renders today\'s breakouts and links into detail', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: "Today's breakouts" })).toBeVisible()

    // At least one breakout card is rendered (and clickable)
    const firstCard = page.locator('a[href^="/breakouts/"]').first()
    await expect(firstCard).toBeVisible({ timeout: 10_000 })

    await firstCard.click()
    await page.waitForURL(/\/breakouts\/[0-9a-f-]+$/)

    // Detail page sanity: symbol header, chart container, stat tiles
    await expect(page.getByRole('heading').first()).toBeVisible()
    await expect(page.getByText('Price', { exact: false }).first()).toBeVisible()
    await expect(page.getByText('Composite score', { exact: false })).toBeVisible()
  })

  test('scans page lists completed runs', async ({ page }) => {
    await page.goto('/scans')
    await expect(page.getByRole('heading', { name: 'Scan history' })).toBeVisible()
    await expect(page.getByText('completed', { exact: false }).first()).toBeVisible({ timeout: 10_000 })
  })

  test('watchlist page renders empty-or-list', async ({ page }) => {
    await page.goto('/watchlist')
    await expect(page.getByRole('heading', { name: 'Watchlist' })).toBeVisible()
    await expect(page.getByPlaceholder('Symbol (e.g. RELIANCE.NS)')).toBeVisible()
  })
})
