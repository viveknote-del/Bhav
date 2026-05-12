export type Exchange = 'NSE' | 'BSE'

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
