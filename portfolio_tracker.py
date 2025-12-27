"""
Portfolio Tracker - Tracks imaginary $300 investment
Run this script to check portfolio status and make trading decisions
"""
import warnings
warnings.filterwarnings('ignore')
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Portfolio file
PORTFOLIO_FILE = Path(__file__).parent / "portfolio_data.json"

def load_portfolio():
    """Load portfolio from JSON file"""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return None

def save_portfolio(data):
    """Save portfolio to JSON file"""
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def init_portfolio():
    """Initialize portfolio with starting position"""
    portfolio = {
        "created": "2025-12-27",
        "initial_budget": 7500000,
        "currency": "VND",
        "cash": 450000,
        "positions": [
            {
                "symbol": "GAS",
                "shares": 100,
                "buy_price": 70500,
                "buy_date": "2025-12-27",
                "buy_cost": 7050000,
                "target": 77550,
                "stop_loss": 66975,
                "status": "OPEN",
                "current_price": 70500,
                "current_value": 7050000,
                "pnl": 0,
                "pnl_percent": 0
            }
        ],
        "closed_positions": [],
        "trades": [
            {
                "date": "2025-12-27",
                "action": "BUY",
                "symbol": "GAS",
                "shares": 100,
                "price": 70500,
                "total": 7050000,
                "reason": "Score +50, UPTREND, Strong momentum"
            }
        ],
        "history": [
            {
                "date": "2025-12-27",
                "total_value": 7500000,
                "cash": 450000,
                "invested": 7050000,
                "pnl": 0,
                "pnl_percent": 0
            }
        ],
        "last_updated": datetime.now().isoformat()
    }
    save_portfolio(portfolio)
    return portfolio

def get_current_price(symbol):
    """Fetch current price from vnstock"""
    try:
        from vnstock import Vnstock
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(
            start=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d')
        )
        if not df.empty:
            return float(df['close'].iloc[-1]) * 1000
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    return None

def analyze_stock(symbol):
    """Run technical analysis on a stock"""
    try:
        from vnstock import Vnstock
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(
            start=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d')
        )

        if df.empty or len(df) < 20:
            return None

        close = df['close']
        price = float(close.iloc[-1]) * 1000

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = float((100 - (100 / (1 + (gain/loss)))).iloc[-1])

        # SMAs
        sma20 = float(close.rolling(20).mean().iloc[-1]) * 1000
        sma50 = float(close.rolling(50).mean().iloc[-1]) * 1000 if len(df) >= 50 else sma20

        # Trend
        if price > sma20 > sma50:
            trend = "UPTREND"
        elif price < sma20 < sma50:
            trend = "DOWNTREND"
        else:
            trend = "SIDEWAYS"

        return {
            "price": price,
            "rsi": rsi,
            "sma20": sma20,
            "sma50": sma50,
            "trend": trend
        }
    except:
        return None

def update_portfolio():
    """Update portfolio with current prices and check signals"""
    portfolio = load_portfolio()
    if not portfolio:
        portfolio = init_portfolio()

    print("=" * 60)
    print("PORTFOLIO UPDATE")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    total_value = portfolio['cash']
    actions = []

    for pos in portfolio['positions']:
        if pos['status'] != 'OPEN':
            continue

        # Get current price
        current_price = get_current_price(pos['symbol'])
        if current_price is None:
            current_price = pos['current_price']
            print(f"Could not fetch price for {pos['symbol']}, using last known: {current_price:,.0f}")

        # Update position
        pos['current_price'] = current_price
        pos['current_value'] = current_price * pos['shares']
        pos['pnl'] = pos['current_value'] - pos['buy_cost']
        pos['pnl_percent'] = (pos['pnl'] / pos['buy_cost']) * 100

        total_value += pos['current_value']

        # Check stop loss
        if current_price <= pos['stop_loss']:
            actions.append({
                "action": "SELL",
                "symbol": pos['symbol'],
                "reason": f"STOP LOSS HIT at {current_price:,.0f} (stop: {pos['stop_loss']:,.0f})",
                "urgent": True
            })
        # Check target
        elif current_price >= pos['target']:
            actions.append({
                "action": "SELL",
                "symbol": pos['symbol'],
                "reason": f"TARGET REACHED at {current_price:,.0f} (target: {pos['target']:,.0f})",
                "urgent": False
            })

        # Print position
        emoji = "🟢" if pos['pnl'] >= 0 else "🔴"
        print(f"\n{emoji} {pos['symbol']}")
        print(f"   Shares: {pos['shares']} @ {pos['buy_price']:,.0f} VND")
        print(f"   Current: {current_price:,.0f} VND")
        print(f"   P&L: {pos['pnl']:+,.0f} VND ({pos['pnl_percent']:+.2f}%)")
        print(f"   Target: {pos['target']:,.0f} | Stop: {pos['stop_loss']:,.0f}")

    # Update totals
    initial = portfolio['initial_budget']
    total_pnl = total_value - initial
    total_pnl_pct = (total_pnl / initial) * 100

    print(f"\n{'='*60}")
    print("PORTFOLIO SUMMARY")
    print(f"{'='*60}")
    print(f"Cash: {portfolio['cash']:,.0f} VND")
    print(f"Invested: {total_value - portfolio['cash']:,.0f} VND")
    print(f"Total Value: {total_value:,.0f} VND")
    print(f"Total P&L: {total_pnl:+,.0f} VND ({total_pnl_pct:+.2f}%)")

    # Record history
    portfolio['history'].append({
        "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "total_value": total_value,
        "cash": portfolio['cash'],
        "invested": total_value - portfolio['cash'],
        "pnl": total_pnl,
        "pnl_percent": total_pnl_pct
    })

    portfolio['last_updated'] = datetime.now().isoformat()

    # Handle actions
    if actions:
        print(f"\n{'='*60}")
        print("⚠️  TRADING SIGNALS")
        print(f"{'='*60}")
        for action in actions:
            print(f"{action['action']}: {action['symbol']} - {action['reason']}")

    save_portfolio(portfolio)

    # Generate dashboard data
    generate_dashboard(portfolio, total_value, total_pnl, total_pnl_pct)

    return portfolio, actions

def generate_dashboard(portfolio, total_value, total_pnl, total_pnl_pct):
    """Generate HTML dashboard for GitHub Pages"""

    positions_html = ""
    for pos in portfolio['positions']:
        if pos['status'] == 'OPEN':
            pnl_class = "positive" if pos['pnl'] >= 0 else "negative"
            positions_html += f"""
            <tr>
                <td><strong>{pos['symbol']}</strong></td>
                <td>{pos['shares']}</td>
                <td>{pos['buy_price']:,.0f}</td>
                <td>{pos['current_price']:,.0f}</td>
                <td class="{pnl_class}">{pos['pnl']:+,.0f} ({pos['pnl_percent']:+.2f}%)</td>
            </tr>
            """

    trades_html = ""
    for trade in portfolio['trades'][-10:]:  # Last 10 trades
        trades_html += f"""
        <tr>
            <td>{trade['date']}</td>
            <td>{trade['action']}</td>
            <td>{trade['symbol']}</td>
            <td>{trade['shares']}</td>
            <td>{trade['price']:,.0f}</td>
        </tr>
        """

    pnl_class = "positive" if total_pnl >= 0 else "negative"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Van's Stock Portfolio</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ color: #60a5fa; margin-bottom: 10px; }}
        .subtitle {{ color: #94a3b8; margin-bottom: 30px; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 20px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .stat {{ background: #1e293b; border-radius: 12px; padding: 20px; text-align: center; }}
        .stat-value {{ font-size: 28px; font-weight: bold; color: #f8fafc; }}
        .stat-label {{ color: #94a3b8; font-size: 14px; margin-top: 5px; }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; font-weight: 500; }}
        .update-time {{ color: #64748b; font-size: 12px; margin-top: 20px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .badge-active {{ background: #22c55e20; color: #22c55e; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Van's Stock Portfolio</h1>
        <p class="subtitle">Algorithmic Trading • Vietnam Market • <span class="badge badge-active">ACTIVE</span></p>

        <div class="stats">
            <div class="stat">
                <div class="stat-value">{total_value:,.0f}</div>
                <div class="stat-label">Total Value (VND)</div>
            </div>
            <div class="stat">
                <div class="stat-value {pnl_class}">{total_pnl:+,.0f}</div>
                <div class="stat-label">Total P&L (VND)</div>
            </div>
            <div class="stat">
                <div class="stat-value {pnl_class}">{total_pnl_pct:+.2f}%</div>
                <div class="stat-label">Return</div>
            </div>
            <div class="stat">
                <div class="stat-value">{portfolio['cash']:,.0f}</div>
                <div class="stat-label">Cash (VND)</div>
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 15px;">Open Positions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Shares</th>
                        <th>Buy Price</th>
                        <th>Current</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody>
                    {positions_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 15px;">Trade History</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Action</th>
                        <th>Symbol</th>
                        <th>Shares</th>
                        <th>Price</th>
                    </tr>
                </thead>
                <tbody>
                    {trades_html}
                </tbody>
            </table>
        </div>

        <p class="update-time">Last updated: {portfolio['last_updated']}</p>
        <p class="update-time">Initial Investment: {portfolio['initial_budget']:,} VND (~$300 USD) on {portfolio['created']}</p>
    </div>
</body>
</html>
"""

    # Save to dashboard folder
    dashboard_path = Path(__file__).parent / "dashboard" / "public" / "portfolio.html"
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Dashboard updated: {dashboard_path}")

def execute_trade(action, symbol, shares, price, reason):
    """Execute a trade and update portfolio"""
    portfolio = load_portfolio()

    if action == "SELL":
        for pos in portfolio['positions']:
            if pos['symbol'] == symbol and pos['status'] == 'OPEN':
                pos['status'] = 'CLOSED'
                pos['sell_price'] = price
                pos['sell_date'] = datetime.now().strftime('%Y-%m-%d')
                pos['final_pnl'] = (price * pos['shares']) - pos['buy_cost']

                # Add cash
                portfolio['cash'] += price * pos['shares']

                # Move to closed
                portfolio['closed_positions'].append(pos.copy())

                # Record trade
                portfolio['trades'].append({
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "action": "SELL",
                    "symbol": symbol,
                    "shares": shares,
                    "price": price,
                    "total": price * shares,
                    "reason": reason
                })

                print(f"✅ SOLD {shares} {symbol} @ {price:,.0f} VND")
                print(f"   P&L: {pos['final_pnl']:+,.0f} VND")
                break

    elif action == "BUY":
        cost = price * shares
        if cost <= portfolio['cash']:
            portfolio['positions'].append({
                "symbol": symbol,
                "shares": shares,
                "buy_price": price,
                "buy_date": datetime.now().strftime('%Y-%m-%d'),
                "buy_cost": cost,
                "target": price * 1.10,
                "stop_loss": price * 0.95,
                "status": "OPEN",
                "current_price": price,
                "current_value": cost,
                "pnl": 0,
                "pnl_percent": 0
            })

            portfolio['cash'] -= cost

            portfolio['trades'].append({
                "date": datetime.now().strftime('%Y-%m-%d'),
                "action": "BUY",
                "symbol": symbol,
                "shares": shares,
                "price": price,
                "total": cost,
                "reason": reason
            })

            print(f"✅ BOUGHT {shares} {symbol} @ {price:,.0f} VND")
        else:
            print(f"❌ Insufficient cash. Need {cost:,.0f}, have {portfolio['cash']:,.0f}")

    save_portfolio(portfolio)
    return portfolio

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'init':
            init_portfolio()
            print("Portfolio initialized!")
        elif cmd == 'update':
            update_portfolio()
    else:
        # Default: update portfolio
        portfolio = load_portfolio()
        if not portfolio:
            print("Initializing new portfolio...")
            portfolio = init_portfolio()

        update_portfolio()
