import { useState, useEffect } from 'react'
import { ArrowUpCircle, ArrowDownCircle, Zap, Bell } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { formatRelativeTime, formatCurrency } from '../utils/format'

interface Activity {
  type: 'trade' | 'signal' | 'deposit' | 'alert'
  description: string
  timestamp: string
  symbol?: string
  amount?: number
}

// Demo activities
const demoActivities: Activity[] = [
  {
    type: 'trade',
    description: 'BUY 100 FPT @ 95,000',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    symbol: 'FPT',
    amount: 9500000,
  },
  {
    type: 'signal',
    description: 'STRONG_BUY signal for VNM (conf: 78%)',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    symbol: 'VNM',
  },
  {
    type: 'deposit',
    description: 'Monthly deposit',
    timestamp: new Date(Date.now() - 86400000).toISOString(),
    amount: 2500000,
  },
  {
    type: 'trade',
    description: 'SELL 50 MSN @ 85,000',
    timestamp: new Date(Date.now() - 172800000).toISOString(),
    symbol: 'MSN',
    amount: 4250000,
  },
  {
    type: 'signal',
    description: 'BUY signal for HPG (conf: 65%)',
    timestamp: new Date(Date.now() - 259200000).toISOString(),
    symbol: 'HPG',
  },
]

export default function ActivityFeed() {
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const { fetchData } = useApi()

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchData<Activity[]>('/dashboard/activity?limit=10')
        if (result && result.length > 0) {
          setActivities(result)
        } else {
          setActivities(demoActivities)
        }
      } catch {
        setActivities(demoActivities)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const getIcon = (type: string) => {
    switch (type) {
      case 'trade':
        return <ArrowUpCircle className="w-5 h-5 text-blue-500" />
      case 'signal':
        return <Zap className="w-5 h-5 text-yellow-500" />
      case 'deposit':
        return <ArrowDownCircle className="w-5 h-5 text-green-500" />
      default:
        return <Bell className="w-5 h-5 text-gray-500" />
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'trade':
        return 'Trade'
      case 'signal':
        return 'Signal'
      case 'deposit':
        return 'Deposit'
      default:
        return 'Alert'
    }
  }

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading activities...</div>
      </div>
    )
  }

  if (activities.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-500">
        No recent activity
      </div>
    )
  }

  return (
    <div className="space-y-4 max-h-80 overflow-y-auto">
      {activities.map((activity, index) => (
        <div
          key={index}
          className="flex items-start gap-3 pb-4 border-b border-gray-50 last:border-0"
        >
          <div className="mt-0.5">{getIcon(activity.type)}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-500 uppercase">
                {getTypeLabel(activity.type)}
              </span>
              {activity.symbol && (
                <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
                  {activity.symbol}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-900 mt-1 truncate">{activity.description}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-gray-400">
                {formatRelativeTime(activity.timestamp)}
              </span>
              {activity.amount && (
                <span className="text-xs text-gray-500">
                  {formatCurrency(activity.amount)}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
