import { useState, useEffect } from 'react'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'
import { useApi } from '../hooks/useApi'
import { formatCompactCurrency, formatDate } from '../utils/format'

interface PerformanceData {
  date: string
  value: number
  pnl: number
  pnl_percent: number
}

// Demo data for when API is unavailable
const generateDemoData = (): PerformanceData[] => {
  const data: PerformanceData[] = []
  const startValue = 2500000
  let currentValue = startValue

  for (let i = 30; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)

    // Add some randomness
    const change = (Math.random() - 0.45) * 100000
    currentValue = Math.max(startValue * 0.8, currentValue + change)

    data.push({
      date: date.toISOString().split('T')[0],
      value: currentValue,
      pnl: currentValue - startValue,
      pnl_percent: ((currentValue - startValue) / startValue) * 100,
    })
  }
  return data
}

export default function PortfolioChart() {
  const [data, setData] = useState<PerformanceData[]>([])
  const [loading, setLoading] = useState(true)
  const { fetchData } = useApi()

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchData<PerformanceData[]>('/dashboard/performance?days=30')
        if (result && result.length > 0) {
          setData(result)
        } else {
          setData(generateDemoData())
        }
      } catch {
        setData(generateDemoData())
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading chart...</div>
      </div>
    )
  }

  const isPositive = data.length > 0 && data[data.length - 1].pnl >= 0

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor={isPositive ? '#10b981' : '#ef4444'}
                stopOpacity={0.3}
              />
              <stop
                offset="95%"
                stopColor={isPositive ? '#10b981' : '#ef4444'}
                stopOpacity={0}
              />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tickFormatter={(value) => {
              const date = new Date(value)
              return `${date.getDate()}/${date.getMonth() + 1}`
            }}
            stroke="#9ca3af"
            fontSize={12}
          />
          <YAxis
            tickFormatter={(value) => formatCompactCurrency(value)}
            stroke="#9ca3af"
            fontSize={12}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '12px',
            }}
            formatter={(value: number) => [formatCompactCurrency(value), 'Value']}
            labelFormatter={(label) => formatDate(label as string)}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={isPositive ? '#10b981' : '#ef4444'}
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorValue)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
