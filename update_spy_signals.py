"""
SPY Signals Auto-Updater
Runs via GitHub Actions after market close each trading day.
Fetches SPY data from Yahoo Finance and updates spy_signals.json.
"""

import json
import os
from datetime import datetime, timezone

import yfinance as yf
import pandas as pd


def calc_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("inf"))
    return 100 - (100 / (1 + rs))


def fetch_spy_news() -> str:
    try:
        news = yf.Ticker("SPY").news
        if news:
            return news[0].get("content", {}).get("title", "")
    except Exception:
        pass
    return ""


def run():
    # Fetch 1 year of daily SPY closes
    df = yf.download("SPY", period="1y", interval="1d", auto_adjust=True, progress=False)

    if df.empty or len(df) < 210:
        raise ValueError(f"Not enough data: {len(df)} rows (need 210+)")

    close = df["Close"].squeeze()

    # Indicators
    rsi2    = calc_rsi(close, period=2)
    sma200  = close.rolling(200).mean()

    last_close  = float(round(close.iloc[-1], 2))
    last_rsi2   = float(round(rsi2.iloc[-1], 2))
    last_sma200 = float(round(sma200.iloc[-1], 2))

    rsi2_below_30  = 1 if last_rsi2 < 30 else 0
    three_lower    = 1 if (close.iloc[-1] < close.iloc[-2] < close.iloc[-3]) else 0
    above_sma200   = 1 if last_close > last_sma200 else 0

    payload = {
        "ticker": "SPY",
        "rsi_2_below_30": rsi2_below_30,
        "three_lower_closes": three_lower,
        "above_sma200": above_sma200,
        "metrics": {
            "last_close": last_close,
            "rsi2": last_rsi2,
            "sma200": last_sma200,
            "news": fetch_spy_news(),
        },
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spy_signals.json")
    with open(out, "w") as f:
        json.dump(payload, f, indent=4)

    print(f"spy_signals.json updated at {payload['updated_at']}")
    print(f"  last_close      = {last_close}")
    print(f"  rsi2            = {last_rsi2}  → rsi_2_below_30  = {rsi2_below_30}")
    print(f"  three_lower     = {three_lower}")
    print(f"  above_sma200    = {above_sma200}")


if __name__ == "__main__":
    run()
