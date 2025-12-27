import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { formatPercent, formatPrice } from '../utils/format'

interface Position {
  symbol: string
  quantity: number
  avg_buy_price: number
  current_price: number | null
  total_cost: number
  current_value: number | null
  unrealized_pnl: number | null
  unrealized_pnl_percent: number | null
}

// Demo positions
const demoPositions: Position[] = [
  {
    symbol: 'FPT',
    quantity: 100,
    avg_buy_price: 95000,
    current_price: 102500,
    total_cost: 9500000,
    current_value: 10250000,
    unrealized_pnl: 750000,
    unrealized_pnl_percent: 7.89,
  },
  {
    symbol: 'VNM',
    quantity: 200,
    avg_buy_price: 72000,
    current_price: 75000,
    total_cost: 14400000,
    current_value: 15000000,
    unrealized_pnl: 600000,
    unrealized_pnl_percent: 4.17,
  },
  {
    symbol: 'HPG',
    quantity: 300,
    avg_buy_price: 28500,
    current_price: 27000,
    total_cost: 8550000,
    current_value: 8100000,
    unrealized_pnl: -450000,
    unrealized_pnl_percent: -5.26,
  },
]

export default function PositionsTable() {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const { fetchData } = useApi()

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchData<Position[]>('/portfolio/positions')
        if (result && result.length > 0) {
          setPositions(result)
        } else {
          setPositions(demoPositions)
        }
      } catch {
        setPositions(demoPositions)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading positions...</div>
      </div>
    )
  }

  if (positions.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-500">
        No positions yet
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="text-left py-3 px-2 font-medium text-gray-500">Symbol</th>
            <th className="text-right py-3 px-2 font-medium text-gray-500">Qty</th>
            <th className="text-right py-3 px-2 font-medium text-gray-500">Avg Price</th>
            <th className="text-right py-3 px-2 font-medium text-gray-500">Current</th>
            <th className="text-right py-3 px-2 font-medium text-gray-500">P&L</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => {
            const pnl = position.unrealized_pnl || 0
            const pnlPercent = position.unrealized_pnl_percent || 0
            const isProfit = pnl >= 0

            return (
              <tr key={position.symbol} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-3 px-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold ${
                      isProfit ? 'bg-green-500' : 'bg-red-500'
                    }`}>
                      {position.symbol.substring(0, 2)}
                    </div>
                    <span className="font-medium text-gray-900">{position.symbol}</span>
                  </div>
                </td>
                <td className="py-3 px-2 text-right text-gray-600">
                  {position.quantity.toLocaleString()}
                </td>
                <td className="py-3 px-2 text-right text-gray-600">
                  {formatPrice(position.avg_buy_price)}
                </td>
                <td className="py-3 px-2 text-right text-gray-900 font-medium">
                  {position.current_price ? formatPrice(position.current_price) : '-'}
                </td>
                <td className="py-3 px-2 text-right">
                  <div className={`flex items-center justify-end gap-1 ${
                    isProfit ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {isProfit ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : (
                      <TrendingDown className="w-4 h-4" />
                    )}
                    <span className="font-medium">{formatPercent(pnlPercent)}</span>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
