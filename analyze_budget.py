"""
Realistic $100 Budget Analysis for Vietnam Stocks
Accounts for minimum lot size of 100 shares
"""
import warnings
warnings.filterwarnings('ignore')

from vnstock import Vnstock
from datetime import datetime, timedelta

BUDGET_VND = 2_500_000  # ~$100 USD
MIN_LOT = 100

# Include more affordable stocks
STOCKS = ['FPT', 'VNM', 'VCB', 'VIC', 'VHM', 'HPG', 'MBB', 'TCB', 'VPB', 'ACB',
          'MSN', 'GAS', 'SAB', 'PLX', 'MWG', 'PNJ', 'SSI', 'CTG', 'STB', 'TPB',
          'VND', 'HDB', 'EIB', 'SHB', 'LPB', 'OCB', 'MSB', 'KDH', 'DGC', 'NLG']

def analyze():
    print('=' * 75)
    print('REALISTIC $100 INVESTMENT ANALYSIS FOR VIETNAM STOCKS')
    print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'Budget: {BUDGET_VND:,} VND (~$100 USD)')
    print(f'Minimum lot size: {MIN_LOT} shares')
    print('=' * 75)
    print()

    results = []
    affordable = []

    for symbol in STOCKS:
        try:
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            df = stock.quote.history(start=start_date, end=end_date)

            if df.empty or len(df) < 50:
                continue

            current_price = float(df['close'].iloc[-1]) * 1000
            min_investment = current_price * MIN_LOT

            close = df['close']

            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # SMAs
            sma20 = float(close.rolling(20).mean().iloc[-1]) * 1000
            sma50 = float(close.rolling(50).mean().iloc[-1]) * 1000

            # Returns
            price_30d = float(df['close'].iloc[-30]) * 1000
            return_30d = ((current_price - price_30d) / price_30d) * 100

            price_7d = float(df['close'].iloc[-7]) * 1000
            return_7d = ((current_price - price_7d) / price_7d) * 100

            # Volume
            avg_vol = df['volume'].tail(20).mean()
            curr_vol = df['volume'].iloc[-1]
            vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1

            # Score
            score = 0
            signals = []

            if rsi < 30:
                score += 30
                signals.append('OVERSOLD')
            elif rsi < 40:
                score += 15
                signals.append('RSI low')
            elif rsi > 70:
                score -= 25
                signals.append('OVERBOUGHT')

            if current_price > sma20 > sma50:
                score += 25
                signals.append('UPTREND')
            elif current_price > sma20:
                score += 10
            elif current_price < sma20 < sma50:
                score -= 20
                signals.append('DOWNTREND')

            if return_7d > 5:
                score += 15
                signals.append('Momentum+')
            elif return_7d > 2:
                score += 5
            elif return_7d < -5:
                score -= 15

            if vol_ratio > 1.5:
                score += 10
                signals.append('HighVol')

            result = {
                'symbol': symbol,
                'price': current_price,
                'min_cost': min_investment,
                'affordable': min_investment <= BUDGET_VND,
                'week': return_7d,
                'month': return_30d,
                'rsi': rsi,
                'score': score,
                'signals': signals
            }
            results.append(result)

            if result['affordable']:
                affordable.append(result)

        except Exception as e:
            continue

    # Sort
    results.sort(key=lambda x: x['score'], reverse=True)
    affordable.sort(key=lambda x: x['score'], reverse=True)

    # Print all results
    print('ALL STOCKS ANALYZED:')
    print('-' * 75)
    print(f"{'STOCK':5} {'PRICE':>10} {'MIN COST':>12} {'AFFORD':>7} {'WEEK':>7} {'RSI':>5} {'SCORE':>6}")
    print('-' * 75)

    for r in results:
        afford = 'YES' if r['affordable'] else 'no'
        print(f"{r['symbol']:5} {r['price']:>10,.0f} {r['min_cost']:>12,.0f} {afford:>7} {r['week']:>+6.1f}% {r['rsi']:>5.1f} {r['score']:>+5d}")

    print()
    print('=' * 75)
    print('AFFORDABLE STOCKS (Can buy 100 shares with 2.5M VND)')
    print('=' * 75)

    if not affordable:
        print('No stocks affordable with current budget!')
        print('Consider increasing budget or buying fractional shares (not available in VN)')
        return

    for i, r in enumerate(affordable, 1):
        sig = 'BUY' if r['score'] >= 25 else ('HOLD' if r['score'] >= 0 else 'AVOID')
        indicator = '>>>' if sig == 'BUY' else '   '
        print(f"{indicator} {i}. {r['symbol']:5} @ {r['price']:,.0f} VND x 100 = {r['min_cost']:,.0f} VND | Score: {r['score']:+d} | {sig}")
        if r['signals']:
            print(f"      Signals: {', '.join(r['signals'])}")

    print()
    print('=' * 75)
    print('MY FINAL RECOMMENDATION WITH $100')
    print('=' * 75)

    # Pick best affordable stock
    buy_picks = [r for r in affordable if r['score'] >= 20]

    if buy_picks:
        # Can we fit 2 stocks?
        if len(buy_picks) >= 2:
            p1, p2 = buy_picks[0], buy_picks[1]
            if p1['min_cost'] + p2['min_cost'] <= BUDGET_VND:
                total = p1['min_cost'] + p2['min_cost']
                print(f"STRATEGY: Split into 2 positions for diversification")
                print()
                print(f"1. BUY {p1['symbol']}: 100 shares @ {p1['price']:,.0f} = {p1['min_cost']:,.0f} VND")
                print(f"   Score: {p1['score']} | RSI: {p1['rsi']:.1f} | 7d: {p1['week']:+.1f}% | 30d: {p1['month']:+.1f}%")
                print()
                print(f"2. BUY {p2['symbol']}: 100 shares @ {p2['price']:,.0f} = {p2['min_cost']:,.0f} VND")
                print(f"   Score: {p2['score']} | RSI: {p2['rsi']:.1f} | 7d: {p2['week']:+.1f}% | 30d: {p2['month']:+.1f}%")
                print()
                print(f"Total: {total:,.0f} VND | Remaining: {BUDGET_VND - total:,.0f} VND")
            else:
                # Just pick best one
                p = buy_picks[0]
                print(f"STRATEGY: Single best pick")
                print()
                print(f"BUY {p['symbol']}: 100 shares @ {p['price']:,.0f} = {p['min_cost']:,.0f} VND")
                print(f"Score: {p['score']} | RSI: {p['rsi']:.1f} | 7d: {p['week']:+.1f}% | 30d: {p['month']:+.1f}%")
                print()
                print(f"Remaining cash: {BUDGET_VND - p['min_cost']:,.0f} VND (save for next month)")
        else:
            p = buy_picks[0]
            print(f"STRATEGY: Single position")
            print()
            print(f"BUY {p['symbol']}: 100 shares @ {p['price']:,.0f} = {p['min_cost']:,.0f} VND")
            print(f"Score: {p['score']} | RSI: {p['rsi']:.1f}")
            print()
            print(f"Remaining: {BUDGET_VND - p['min_cost']:,.0f} VND")
    else:
        print("NO STRONG BUY SIGNALS among affordable stocks.")
        print()
        print("RECOMMENDATION: HOLD CASH this month")
        print("Wait for better opportunities or market correction.")
        print()
        best = affordable[0] if affordable else None
        if best:
            print(f"Closest candidate: {best['symbol']} (Score: {best['score']})")
            print("Not strong enough to recommend buying now.")

    print()
    print('=' * 75)
    print('DISCLAIMER: Algorithmic analysis only. Not financial advice.')
    print('=' * 75)

if __name__ == '__main__':
    analyze()
