# Vietnam Stock Trader

An automated stock trading system for the Vietnamese stock market (HOSE, HNX, UPCOM) with real-time dashboard, news sentiment analysis, and SSI FastConnect API integration.

## Features

- **Automated Trading**: Execute trades automatically based on technical analysis and sentiment signals
- **SSI FastConnect Integration**: Direct API integration with SSI Securities for order execution
- **Real-time Dashboard**: Monitor your portfolio, balance, and market data via web dashboard
- **News Sentiment Analysis**: Fetch news from Vietnamese sources (CafeF, VnExpress, VietStock) and analyze sentiment
- **Technical Analysis**: RSI, MACD, Bollinger Bands, SMA crossovers, and more
- **Risk Management**: Position sizing, stop-loss, maximum portfolio allocation rules
- **Telegram Notifications**: Get alerts for trades, signals, and daily summaries

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    VIETNAM STOCK TRADER                       │
├──────────────────────────────────────────────────────────────┤
│  Backend (Python/FastAPI)          Dashboard (React/Vite)     │
│  ├── SSI FastConnect API           ├── Portfolio Overview     │
│  ├── vnstock Market Data           ├── Real-time Charts       │
│  ├── News Sentiment Analysis       ├── Trade History          │
│  ├── Strategy Engine               ├── Market News            │
│  ├── SQLite Database               └── Settings               │
│  └── Scheduled Tasks                                          │
└──────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Python 3.11+** for backend
- **Node.js 18+** for dashboard
- **SSI Securities Account** (for live trading)
- **ACB or other Vietnamese bank account** linked to SSI

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/van31337/vietnam-stock-trader.git
cd vietnam-stock-trader
```

### 2. Setup Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp ../.env.example ../.env
# Edit .env with your credentials
```

### 4. Run Backend Server

```bash
python run.py
```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

### 5. Setup Dashboard

```bash
cd ../dashboard
npm install
npm run dev
```

Dashboard will be available at `http://localhost:3000`

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# SSI FastConnect API (get from SSI iBoard)
SSI_CONSUMER_ID=your_consumer_id
SSI_CONSUMER_SECRET=your_consumer_secret
SSI_TRADING_ACCOUNT=your_account_number

# Trading settings
MONTHLY_BUDGET_VND=2500000  # ~$100 USD
MAX_STOCKS_IN_PORTFOLIO=5
MAX_LOSS_PER_TRADE_PERCENT=2.0

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Enable auto-trading (only after testing!)
ENABLE_AUTO_TRADING=false
```

## Getting SSI API Access

1. Open an account at [SSI Securities](https://www.ssi.com.vn)
2. Link your ACB bank account
3. Visit any SSI branch with your CCCD (citizen ID)
4. Request FastConnect API access (free)
5. Get credentials from SSI iBoard: Dịch vụ & Tiện ích > Dịch vụ API

Full documentation: https://guide.ssi.com.vn/ssi-products

## API Endpoints

### Portfolio
- `GET /portfolio/summary` - Get portfolio summary
- `GET /portfolio/positions` - Get current positions
- `GET /portfolio/balance` - Get cash balance
- `POST /portfolio/deposit` - Record a deposit

### Trading
- `POST /trading/order` - Place an order
- `GET /trading/trades` - Get trade history
- `POST /trading/analyze` - Analyze a stock
- `GET /trading/top-picks` - Get stock recommendations

### Market Data
- `GET /market/overview` - Get VN-Index overview
- `GET /market/quote/{symbol}` - Get stock quote
- `GET /market/history/{symbol}` - Get price history
- `GET /market/news` - Get latest news

### Dashboard
- `GET /dashboard/summary` - Dashboard summary
- `GET /dashboard/performance` - Portfolio performance chart
- `GET /dashboard/activity` - Recent activity

## Trading Strategy

The system uses a multi-factor approach:

1. **Technical Analysis (40%)**
   - RSI (oversold/overbought)
   - MACD crossovers
   - SMA trend (20/50/200)
   - Bollinger Bands
   - Volume analysis

2. **Sentiment Analysis (35%)**
   - News from CafeF, VnExpress, VietStock
   - Vietnamese language processing
   - Impact scoring

3. **Fundamental Analysis (25%)**
   - P/E ratio
   - ROE
   - Debt/Equity ratio

### Risk Management

- Focus on VN30 blue-chip stocks
- Maximum 5 stocks in portfolio
- 2% maximum loss per trade (stop-loss)
- Dollar Cost Averaging approach
- Monthly budget allocation

## Scheduling

Vietnam market hours (UTC+7):
- Morning: 09:00 - 11:30
- Afternoon: 13:00 - 15:00

Scheduled tasks:
- 08:30 - Pre-market analysis
- 09:05 - Market open check
- 11:00 - Mid-day review
- 13:30 - Afternoon analysis
- 15:05 - Market close summary
- 17:00 - Post-market reporting

## Dashboard Deployment

Deploy to GitHub Pages:

```bash
cd dashboard
npm run build
npm run deploy
```

Dashboard URL: https://van31337.github.io/vietnam-stock-trader

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- SQLAlchemy + SQLite
- vnstock (market data)
- APScheduler
- TextBlob / underthesea (sentiment)

**Frontend:**
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Recharts

## License

MIT License - See LICENSE file

## Disclaimer

This software is for educational purposes. Trading stocks involves risk. The authors are not responsible for any financial losses. Always do your own research before investing.

## Support

- SSI API Docs: https://guide.ssi.com.vn/ssi-products
- vnstock Docs: https://docs.vnstock.site/
- Issues: https://github.com/van31337/vietnam-stock-trader/issues
