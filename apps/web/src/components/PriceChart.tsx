'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, Time } from 'lightweight-charts'
import type { Bar } from '@/types'

interface Props {
  bars: Bar[]
  breakoutLevel?: number | null
  breakoutDate?: string | null
  height?: number
}

export function PriceChart({ bars, breakoutLevel, breakoutDate, height = 380 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: '#09090b' },
        textColor: '#d4d4d8',
      },
      grid: {
        vertLines: { color: '#18181b' },
        horzLines: { color: '#18181b' },
      },
      rightPriceScale: { borderColor: '#27272a' },
      timeScale: { borderColor: '#27272a' },
    })
    chartRef.current = chart

    candleSeriesRef.current = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })

    volumeSeriesRef.current = chart.addHistogramSeries({
      color: '#3f3f46',
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    })
    chart.priceScale('').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    const onResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      chart.remove()
      chartRef.current = null
    }
  }, [height])

  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return

    const candles = bars.map((b) => ({
      time: b.date as Time,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }))
    const volumes = bars.map((b) => ({
      time: b.date as Time,
      value: b.volume,
      color: b.close >= b.open ? '#22c55e44' : '#ef444444',
    }))

    candleSeriesRef.current.setData(candles)
    volumeSeriesRef.current.setData(volumes)

    if (breakoutLevel) {
      candleSeriesRef.current.createPriceLine({
        price: breakoutLevel,
        color: '#a3a3a3',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'Break level',
      })
    }
    if (breakoutDate && bars.some((b) => b.date === breakoutDate)) {
      candleSeriesRef.current.setMarkers([{
        time: breakoutDate as Time,
        position: 'belowBar',
        color: '#fbbf24',
        shape: 'arrowUp',
        text: 'Breakout',
      }])
    }

    chartRef.current?.timeScale().fitContent()
  }, [bars, breakoutLevel, breakoutDate])

  return <div ref={containerRef} className="w-full" />
}
