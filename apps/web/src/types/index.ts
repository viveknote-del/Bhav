export type Exchange = 'NSE' | 'BSE'

export type BreakoutType =
  | 'FIFTY_TWO_WEEK_HIGH'
  | 'CONSOLIDATION'
  | 'VOLUME_SPIKE'
  | 'PATTERN'

export type PatternSubtype = 'FLAG' | 'CUP_HANDLE' | 'TRIANGLE'

export type ScanType = 'EOD' | 'INTRADAY'
export type ScanStatus = 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface Instrument {
  symbol: string
  exchange: Exchange
  name: string
  sector: string | null
  industry: string | null
  market_cap: number | null
  is_active: boolean
  updated_at: string
}

export interface InstrumentList {
  items: Instrument[]
  total: number
  page: number
  limit: number
}

export interface Bar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface Chart {
  symbol: string
  bars: Bar[]
}

export interface NewsLink {
  title: string
  url: string
  source: string
  published_at: string
}

export interface Breakout {
  id: string
  scan_run_id: string
  symbol: string
  detected_at: string
  breakout_type: BreakoutType
  pattern_subtype: PatternSubtype | null
  price: number
  breakout_level: number | null
  volume_ratio: number | null
  composite_score: number
  indicators: Record<string, number | string | boolean> | null
  ai_commentary: string | null
  news_links: NewsLink[] | null
}

export interface BreakoutList {
  items: Breakout[]
  total: number
  page: number
  limit: number
}

export interface ScanRun {
  id: string
  started_at: string
  finished_at: string | null
  scan_type: ScanType
  universe_size: number | null
  breakouts_found: number | null
  status: ScanStatus
  error: string | null
  summary: string | null
}

export interface ScanRunList {
  items: ScanRun[]
  total: number
  page: number
  limit: number
}

export interface ScanDetail {
  scan: ScanRun
  breakouts: Breakout[]
}

export interface WatchlistItem {
  symbol: string
  name: string
  sector: string | null
  exchange: Exchange
  notes: string | null
  added_at: string
}
