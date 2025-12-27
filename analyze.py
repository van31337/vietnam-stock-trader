"""
Real-time Vietnam Stock Analysis
Analyzes VN30 stocks and provides investment recommendations
"""
import warnings
warnings.filterwarnings('ignore')
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from vnstock import Vnstock
from datetime import datetime, timedelta

# VN30 stocks
VN30 = ['FPT', 'VNM', 'VCB', 'VIC', 'VHM', 'HPG', 'MBB', 'TCB', 'VPB', 'ACB',
        'MSN', 'GAS', 'SAB', 'PLX', 'MWG', 'PNJ', 'SSI', 'CTG', 'STB', 'TPB']

def analyze_stocks():
    print('=' * 70)
    print('REAL-TIME VIETNAM STOCK ANALYSIS')
    print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('Budget: 2,500,000 VND (~$100 USD)')
    print('=' * 70)
    print()

    results = []

    for symbol in VN30:
        try:
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            df = stock.quote.history(start=start_date, end=end_date)

            if df.empty or len(df) < 50:
                continue

            # Prices - vnstock returns in 1000 VND
            current_price = float(df['close'].iloc[-1]) * 1000
            prev_close = float(df['close'].iloc[-2]) * 1000

            close = df['close']

            # RSI 14
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # SMAs
            sma20 = float(close.rolling(20).mean().iloc[-1]) * 1000
            sma50 = float(close.rolling(50).mean().iloc[-1]) * 1000

            # MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd = ema12 - ema26
            signal_line = macd.ewm(span=9).mean()
            macd_hist = float((macd - signal_line).iloc[-1])

            # Returns
            daily_return = ((current_price - prev_close) / prev_close) * 100

            price_30d = float(df['close'].iloc[-30]) * 1000
            return_30d = ((current_price - price_30d) / price_30d) * 100

            price_7d = float(df['close'].iloc[-7]) * 1000
            return_7d = ((current_price - price_7d) / price_7d) * 100

            # Volume
            avg_vol = df['volume'].tail(20).mean()
            curr_vol = df['volume'].iloc[-1]
            vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1

            # Scoring
            score = 0
            signals = []

            # RSI
            if rsi < 30:
                score += 30
                signals.append('OVERSOLD')
            elif rsi < 40:
                score += 15
                signals.append('RSI low')
            elif rsi > 70:
                score -= 25
                signals.append('OVERBOUGHT')
            elif rsi > 60:
                score -= 10

            # Trend
            if current_price > sma20 > sma50:
                score += 25
                signals.append('UPTREND')
            elif current_price > sma20:
                score += 10
            elif current_price < sma20 < sma50:
                score -= 20
                signals.append('DOWNTREND')
            elif current_price < sma20:
                score -= 10

            # MACD
            if macd_hist > 0:
                score += 10
            else:
                score -= 5

            # Momentum
            if return_7d > 5:
                score += 15
                signals.append('Strong momentum')
            elif return_7d > 2:
                score += 5
            elif return_7d < -5:
                score -= 15
            elif return_7d < -2:
                score -= 5

            # Volume
            if vol_ratio > 1.5:
                score += 10
                signals.append('High volume')

            results.append({
                'symbol': symbol,
                'price': current_price,
                'daily': daily_return,
                'week': return_7d,
                'month': return_30d,
                'rsi': rsi,
                'score': score,
                'signals': signals
            })

        except Exception as e:
            continue

    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)

    # Print results
    print('ANALYSIS RESULTS (Ranked by Score)')
    print('-' * 70)
    print(f"{'#':>2} {'STOCK':5} {'PRICE':>12} {'DAY':>7} {'WEEK':>7} {'MONTH':>7} {'RSI':>5} {'SCORE':>6} {'SIGNAL'}")
    print('-' * 70)

    for i, r in enumerate(results, 1):
        sig = 'BUY' if r['score'] >= 25 else ('HOLD' if r['score'] >= 0 else 'SELL')
        print(f"{i:>2} {r['symbol']:5} {r['price']:>10,.0f}d {r['daily']:>+6.1f}% {r['week']:>+6.1f}% {r['month']:>+6.1f}% {r['rsi']:>5.1f} {r['score']:>+5d}  {sig}")
        if r['signals']:
            print(f"   --> {', '.join(r['signals'])}")

    print()
    print('=' * 70)
    print('MY $100 INVESTMENT DECISION')
    print('=' * 70)

    buy_candidates = [r for r in results if r['score'] >= 25]
    budget = 2500000

    if len(buy_candidates) >= 2:
        picks = buy_candidates[:min(3, len(buy_candidates))]
        per_stock = budget // len(picks)

        print(f'Strategy: Diversify into {len(picks)} high-score stocks')
        print(f'Budget per position: {per_stock:,} VND')
        print()

        total = 0
        for p in picks:
            shares = max(100, (per_stock // int(p['price']) // 100) * 100)
            cost = shares * p['price']
            total += cost
            target = p['price'] * 1.10
            stop = p['price'] * 0.95

            print(f">>> BUY {p['symbol']}")
            print(f"    Shares: {shares:,} @ {p['price']:,.0f} VND = {cost:,.0f} VND")
            print(f"    RSI: {p['rsi']:.1f} | 30d Return: {p['month']:+.1f}%")
            print(f"    Target: {target:,.0f} VND (+10%) | Stop: {stop:,.0f} VND (-5%)")
            print()

        print(f'Total Invested: {total:,.0f} VND')
        print(f'Cash Reserve: {budget - total:,.0f} VND')

    elif len(buy_candidates) == 1:
        p = buy_candidates[0]
        shares = max(100, (int(budget * 0.7) // int(p['price']) // 100) * 100)
        cost = shares * p['price']

        print('Strategy: Single strong pick + cash reserve')
        print()
        print(f">>> BUY {p['symbol']}")
        print(f"    Shares: {shares:,} @ {p['price']:,.0f} = {cost:,.0f} VND")
        print(f"    Cash Reserve: {budget - cost:,.0f} VND (30%)")

    else:
        print('RECOMMENDATION: STAY IN CASH')
        print()
        print('No stocks show strong buy signals at the moment.')
        print('The market appears weak or uncertain.')
        print('Wait for better entry points.')

    print()
    print('=' * 70)
    print('RISK WARNING: This is algorithmic analysis, not financial advice.')
    print('=' * 70)

    return results

if __name__ == '__main__':
    analyze_stocks()
