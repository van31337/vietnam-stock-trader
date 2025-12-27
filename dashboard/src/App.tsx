import { useState, useEffect } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  PieChart,
  Activity,
  RefreshCw,
  Settings,
  Bell,
  Clock,
  DollarSign,
  BarChart3,
  Newspaper
} from 'lucide-react'
import PortfolioChart from './components/PortfolioChart'
import PositionsTable from './components/PositionsTable'
import ActivityFeed from './components/ActivityFeed'
import MarketOverview from './components/MarketOverview'
import { useApi } from './hooks/useApi'
import { formatCurrency, formatPercent } from './utils/format'

interface DashboardSummary {
  total_portfolio_value: number
  cash_balance: number
  total_invested: number
  total_pnl: number
  total_pnl_percent: number
  num_positions: number
  market_status: string
  ssi_connected: boolean
  auto_trading_enabled: boolean
  last_updated: string
}

function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
  const { fetchData, apiUrl } = useApi()

  const loadDashboard = async () => {
    setLoading(true)
    try {
      const data = await fetchData<DashboardSummary>('/dashboard/summary')
      setSummary(data)
      setError(null)
      setLastRefresh(new Date())
    } catch (err) {
      setError('Could not connect to trading server')
      // Use demo data for GitHub Pages
      setSummary({
        total_portfolio_value: 5250000,
        cash_balance: 1250000,
        total_invested: 4000000,
        total_pnl: 375000,
        total_pnl_percent: 9.38,
        num_positions: 3,
        market_status: 'CLOSED',
        ssi_connected: false,
        auto_trading_enabled: false,
        last_updated: new Date().toISOString()
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
    // Refresh every 60 seconds
    const interval = setInterval(loadDashboard, 60000)
    return () => clearInterval(interval)
  }, [])

  const isProfitable = (summary?.total_pnl || 0) >= 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Vietnam Stock Trader</h1>
                <p className="text-xs text-gray-500">Automated Trading Dashboard</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4 text-gray-400" />
                <span className="text-gray-600">
                  Last update: {lastRefresh.toLocaleTimeString()}
                </span>
              </div>

              <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                summary?.market_status === 'OPEN'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                Market {summary?.market_status || 'CLOSED'}
              </div>

              <button
                onClick={loadDashboard}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                disabled={loading}
              >
                <RefreshCw className={`w-5 h-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
              </button>

              <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <Bell className="w-5 h-5 text-gray-600" />
              </button>

              <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <Settings className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-800 text-sm">
              <strong>Demo Mode:</strong> {error}. Showing sample data.
            </p>
            <p className="text-yellow-700 text-xs mt-1">
              API URL: {apiUrl}
            </p>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Portfolio Value */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-500 text-sm">Total Portfolio</span>
              <div className="p-2 bg-primary-50 rounded-lg">
                <Wallet className="w-5 h-5 text-primary-600" />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(summary?.total_portfolio_value || 0)}
            </div>
            <div className={`flex items-center gap-1 mt-2 text-sm ${isProfitable ? 'stat-positive' : 'stat-negative'}`}>
              {isProfitable ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              <span>{formatPercent(summary?.total_pnl_percent || 0)} all time</span>
            </div>
          </div>

          {/* Cash Balance */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-500 text-sm">Cash Balance</span>
              <div className="p-2 bg-green-50 rounded-lg">
                <DollarSign className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {formatCurrency(summary?.cash_balance || 0)}
            </div>
            <div className="text-gray-500 text-sm mt-2">
              Available for trading
            </div>
          </div>

          {/* Total P&L */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-500 text-sm">Total P&L</span>
              <div className={`p-2 rounded-lg ${isProfitable ? 'bg-green-50' : 'bg-red-50'}`}>
                <BarChart3 className={`w-5 h-5 ${isProfitable ? 'text-green-600' : 'text-red-600'}`} />
              </div>
            </div>
            <div className={`text-2xl font-bold ${isProfitable ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(summary?.total_pnl || 0, true)}
            </div>
            <div className="text-gray-500 text-sm mt-2">
              From {formatCurrency(summary?.total_invested || 0)} invested
            </div>
          </div>

          {/* Positions */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-500 text-sm">Open Positions</span>
              <div className="p-2 bg-purple-50 rounded-lg">
                <PieChart className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {summary?.num_positions || 0}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className={`px-2 py-0.5 rounded text-xs ${
                summary?.auto_trading_enabled
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-600'
              }`}>
                {summary?.auto_trading_enabled ? 'Auto-trading ON' : 'Auto-trading OFF'}
              </span>
            </div>
          </div>
        </div>

        {/* Charts and Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Portfolio Chart */}
          <div className="lg:col-span-2 card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">Portfolio Performance</h2>
              <div className="flex gap-2">
                <button className="btn-primary text-sm">1M</button>
                <button className="btn-secondary text-sm">3M</button>
                <button className="btn-secondary text-sm">1Y</button>
              </div>
            </div>
            <PortfolioChart />
          </div>

          {/* Activity Feed */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
              <Activity className="w-5 h-5 text-gray-400" />
            </div>
            <ActivityFeed />
          </div>
        </div>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Positions Table */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">Current Positions</h2>
              <button className="btn-secondary text-sm">View All</button>
            </div>
            <PositionsTable />
          </div>

          {/* Market Overview */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">Market Overview</h2>
              <Newspaper className="w-5 h-5 text-gray-400" />
            </div>
            <MarketOverview />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-sm text-gray-500">
              Vietnam Stock Trader v1.0.0 | {summary?.ssi_connected ? 'SSI Connected' : 'SSI Disconnected'}
            </div>
            <div className="flex gap-4 text-sm text-gray-500">
              <a href="https://guide.ssi.com.vn/ssi-products" target="_blank" rel="noopener noreferrer" className="hover:text-primary-600">
                SSI API Docs
              </a>
              <a href="https://docs.vnstock.site/" target="_blank" rel="noopener noreferrer" className="hover:text-primary-600">
                vnstock Docs
              </a>
              <a href="https://github.com/van31337/vietnam-stock-trader" target="_blank" rel="noopener noreferrer" className="hover:text-primary-600">
                GitHub
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
