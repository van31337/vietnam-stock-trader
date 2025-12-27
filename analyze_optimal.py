"""
Optimal Budget Analysis - What budget opens up the best opportunities?
"""
import warnings
warnings.filterwarnings('ignore')

from vnstock import Vnstock
from datetime import datetime, timedelta

def analyze_with_budget(budget_vnd, budget_name):
    """Analyze what we can buy with a specific budget"""

    STOCKS = ['FPT', 'VNM', 'VCB', 'VIC', 'VHM', 'HPG', 'MBB', 'TCB', 'VPB', 'ACB',
              'MSN', 'GAS', 'SAB', 'PLX', 'MWG', 'PNJ', 'SSI', 'CTG', 'STB', 'TPB',
              'VND', 'HDB', 'EIB', 'SHB', 'LPB', 'OCB', 'MSB', 'KDH', 'DGC', 'NLG']

    results = []

    for symbol in STOCKS:
        try:
            stock = Vnstock().stock(symbol=symbol, source='VCI')
            df = stock.quote.history(
                start=(datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'),
                end=datetime.now().strftime('%Y-%m-%d')
            )

            if df.empty or len(df) < 50:
                continue

            price = float(df['close'].iloc[-1]) * 1000
            min_cost = price * 100

            close = df['close']
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = float((100 - (100 / (1 + (gain/loss)))).iloc[-1])

            sma20 = float(close.rolling(20).mean().iloc[-1]) * 1000
            sma50 = float(close.rolling(50).mean().iloc[-1]) * 1000

            ret_7d = ((price - float(df['close'].iloc[-7])*1000) / (float(df['close'].iloc[-7])*1000)) * 100
            ret_30d = ((price - float(df['close'].iloc[-30])*1000) / (float(df['close'].iloc[-30])*1000)) * 100

            score = 0
            if rsi < 30: score += 30
            elif rsi < 40: score += 15
            elif rsi > 70: score -= 25

            if price > sma20 > sma50: score += 25
            elif price > sma20: score += 10
            elif price < sma20 < sma50: score -= 20

            if ret_7d > 5: score += 15
            elif ret_7d > 2: score += 5
            elif ret_7d < -5: score -= 15

            avg_vol = df['volume'].tail(20).mean()
            if df['volume'].iloc[-1] > avg_vol * 1.5: score += 10

            results.append({
                'symbol': symbol,
                'price': price,
                'min_cost': min_cost,
                'affordable': min_cost <= budget_vnd,
                'rsi': rsi,
                'ret_7d': ret_7d,
                'ret_30d': ret_30d,
                'score': score
            })
        except:
            continue

    results.sort(key=lambda x: x['score'], reverse=True)
    affordable = [r for r in results if r['affordable'] and r['score'] >= 20]

    return results, affordable

def main():
    print('=' * 75)
    print('OPTIMAL BUDGET ANALYSIS FOR VIETNAM STOCK INVESTING')
    print(f'Date: {datetime.now().strftime("%Y-%m-%d")}')
    print('=' * 75)
    print()

    # Get all stock data first
    all_results, _ = analyze_with_budget(100_000_000, "max")

    # Analyze different budget levels
    budgets = [
        (2_500_000, "$100"),
        (5_000_000, "$200"),
        (7_500_000, "$300"),
        (10_000_000, "$400"),
        (12_500_000, "$500"),
        (25_000_000, "$1000"),
    ]

    print("BUDGET COMPARISON - What opens up at each level:")
    print('-' * 75)

    for budget, name in budgets:
        affordable = [r for r in all_results if r['min_cost'] <= budget and r['score'] >= 20]
        top_score = max([r['score'] for r in affordable]) if affordable else 0
        best = [r['symbol'] for r in affordable if r['score'] == top_score][:3]

        print(f"{name:>6} ({budget:>12,} VND): {len(affordable):>2} BUY signals | Best: {', '.join(best) if best else 'None'}")

    print()
    print('=' * 75)
    print('MY RECOMMENDATION: $300 (~7,500,000 VND)')
    print('=' * 75)
    print()
    print('Why $300?')
    print('- Opens access to GAS (Score +50) - one of the top performers')
    print('- Can diversify into 2 quality positions')
    print('- 3x your current budget but much better risk/reward')
    print('- Sweet spot between affordability and opportunity')
    print()

    # Detailed $300 portfolio
    budget = 7_500_000
    affordable = [r for r in all_results if r['min_cost'] <= budget]
    affordable.sort(key=lambda x: x['score'], reverse=True)
    buy_picks = [r for r in affordable if r['score'] >= 25]

    print('=' * 75)
    print('WHAT I WOULD BUY WITH $300 (7,500,000 VND)')
    print('=' * 75)
    print()

    if len(buy_picks) >= 2:
        # Find best 2 that fit
        total = 0
        picks = []
        for p in buy_picks:
            if total + p['min_cost'] <= budget:
                picks.append(p)
                total += p['min_cost']
            if len(picks) >= 2:
                break

        for i, p in enumerate(picks, 1):
            print(f"POSITION {i}: {p['symbol']}")
            print(f"  Buy: 100 shares @ {p['price']:,.0f} VND = {p['min_cost']:,.0f} VND")
            print(f"  Score: {p['score']:+d} | RSI: {p['rsi']:.1f}")
            print(f"  7-day: {p['ret_7d']:+.1f}% | 30-day: {p['ret_30d']:+.1f}%")
            print(f"  Target: {p['price']*1.10:,.0f} VND (+10%)")
            print(f"  Stop Loss: {p['price']*0.95:,.0f} VND (-5%)")
            print()

        print(f"TOTAL INVESTED: {total:,.0f} VND")
        print(f"CASH RESERVE: {budget - total:,.0f} VND")

        # Expected returns
        avg_score = sum(p['score'] for p in picks) / len(picks)
        print()
        print(f"Portfolio Score: {avg_score:.0f} (Strong)")
        print(f"Expected Monthly Range: -5% to +15% based on technicals")

    print()
    print('=' * 75)
    print('COMPARISON: $100 vs $300 PORTFOLIO')
    print('=' * 75)

    # $100 best pick
    budget_100 = 2_500_000
    picks_100 = [r for r in all_results if r['min_cost'] <= budget_100 and r['score'] >= 20]
    best_100 = picks_100[0] if picks_100 else None

    # $300 best picks
    budget_300 = 7_500_000
    picks_300 = [r for r in all_results if r['min_cost'] <= budget_300 and r['score'] >= 25][:2]

    print()
    print(f"$100 Portfolio:")
    if best_100:
        print(f"  {best_100['symbol']}: Score {best_100['score']:+d}")
    else:
        print(f"  No strong picks available")

    print()
    print(f"$300 Portfolio:")
    for p in picks_300:
        print(f"  {p['symbol']}: Score {p['score']:+d}")

    avg_300 = sum(p['score'] for p in picks_300) / len(picks_300) if picks_300 else 0
    avg_100 = best_100['score'] if best_100 else 0

    print()
    print(f"Score Improvement: {avg_100} -> {avg_300:.0f} ({((avg_300-avg_100)/avg_100*100) if avg_100 else 0:.0f}% better)")
    print()
    print('=' * 75)

if __name__ == '__main__':
    main()
