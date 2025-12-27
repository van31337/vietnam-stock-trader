import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, ExternalLink } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { formatPrice, formatPercent } from '../utils/format'

interface MarketData {
  index_name: string
  value: number
  change: number
  change_percent: number
  volume: number
  market_status: string
}

interface NewsItem {
  title: string
  source: string
  url: string
  published: string | null
  symbols: string[]
}

// Demo data
const demoMarketData: MarketData = {
  index_name: 'VN-Index',
  value: 1245.67,
  change: 12.34,
  change_percent: 1.0,
  volume: 523456789,
  market_status: 'CLOSED',
}

const demoNews: NewsItem[] = [
  {
    title: 'VN-Index vượt mốc 1,250 điểm, khối ngoại mua ròng mạnh',
    source: 'CafeF',
    url: 'https://cafef.vn',
    published: new Date().toISOString(),
    symbols: ['VNM', 'VIC'],
  },
  {
    title: 'FPT công bố kết quả kinh doanh quý 4 vượt kỳ vọng',
    source: 'VnExpress',
    url: 'https://vnexpress.net',
    published: new Date(Date.now() - 3600000).toISOString(),
    symbols: ['FPT'],
  },
  {
    title: 'Ngân hàng đồng loạt tăng lãi suất tiền gửi',
    source: 'VietStock',
    url: 'https://vietstock.vn',
    published: new Date(Date.now() - 7200000).toISOString(),
    symbols: ['VCB', 'TCB', 'MBB'],
  },
]

export default function MarketOverview() {
  const [marketData, setMarketData] = useState<MarketData | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const { fetchData } = useApi()

  useEffect(() => {
    const loadData = async () => {
      try {
        const [market, newsData] = await Promise.all([
          fetchData<MarketData>('/market/overview'),
          fetchData<NewsItem[]>('/dashboard/news-feed?limit=5'),
        ])
        setMarketData(market || demoMarketData)
        setNews(newsData && newsData.length > 0 ? newsData : demoNews)
      } catch {
        setMarketData(demoMarketData)
        setNews(demoNews)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading market data...</div>
      </div>
    )
  }

  const isPositive = (marketData?.change || 0) >= 0

  return (
    <div className="space-y-6">
      {/* Index Overview */}
      {marketData && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">{marketData.index_name}</div>
              <div className="text-2xl font-bold text-gray-900">
                {marketData.value.toFixed(2)}
              </div>
            </div>
            <div className={`flex items-center gap-2 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? (
                <TrendingUp className="w-5 h-5" />
              ) : (
                <TrendingDown className="w-5 h-5" />
              )}
              <div className="text-right">
                <div className="font-semibold">
                  {isPositive ? '+' : ''}{marketData.change.toFixed(2)}
                </div>
                <div className="text-sm">
                  {formatPercent(marketData.change_percent)}
                </div>
              </div>
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Volume: {(marketData.volume / 1000000).toFixed(1)}M shares
          </div>
        </div>
      )}

      {/* News Feed */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">Latest News</h3>
        <div className="space-y-3">
          {news.map((item, index) => (
            <a
              key={index}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 line-clamp-2 group-hover:text-primary-600">
                    {item.title}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-500">{item.source}</span>
                    {item.symbols.length > 0 && (
                      <div className="flex gap-1">
                        {item.symbols.slice(0, 3).map((symbol) => (
                          <span
                            key={symbol}
                            className="text-xs bg-primary-100 text-primary-700 px-1.5 py-0.5 rounded"
                          >
                            {symbol}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-primary-600 flex-shrink-0" />
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
