"""Simple Backtest System"""
import numpy as np


def run_backtest(df, signal_history: list) -> dict:
    if not signal_history or len(signal_history) < 3:
        return {
            "win_rate": 0, "profit_factor": 0, "max_dd": 0,
            "total_trades": 0, "net_return": 0, "equity_curve": [100],
        }

    closes = df['Close'].values
    n = len(closes)

    wins = 0
    losses = 0
    profits = []
    equity = [100.0]
    max_equity = 100.0
    max_dd = 0.0

    for i, sig in enumerate(signal_history[:-1]):
        next_sig = signal_history[i + 1]
        entry_idx = sig['index']
        exit_idx = min(next_sig['index'], n - 1)

        entry_price = sig['price']
        exit_price = closes[exit_idx]

        if sig['type'] == 'BUY':
            ret = (exit_price - entry_price) / entry_price * 100
        else:
            ret = (entry_price - exit_price) / entry_price * 100

        # Simple 2% risk per trade
        pnl = ret * 0.5  # half position
        equity.append(equity[-1] * (1 + pnl / 100))
        profits.append(pnl)

        if pnl > 0:
            wins += 1
        else:
            losses += 1

        max_equity = max(max_equity, equity[-1])
        dd = (max_equity - equity[-1]) / max_equity * 100
        max_dd = max(max_dd, dd)

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    pos_sum = sum(p for p in profits if p > 0)
    neg_sum = abs(sum(p for p in profits if p < 0))
    profit_factor = pos_sum / neg_sum if neg_sum > 0 else pos_sum

    net_return = (equity[-1] - 100) if len(equity) > 1 else 0

    return {
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_dd": max_dd,
        "total_trades": total,
        "net_return": net_return,
        "equity_curve": equity,
    }
