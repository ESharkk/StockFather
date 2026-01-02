import time
import threading
import concurrent.futures
from typing import Dict, List, Optional

import yfinance as yf
from services.universe import load_sp500

UNIVERSE = load_sp500()[:50]

MAX_WORKERS = 8
CACHE_TTL = 300  # seconds


_history_cache: Dict[str, Dict] = {}
_history_cache_time: Dict[str, float] = {}

_result_cache: Dict[str, Dict] = {}
_result_cache_time: Dict[str, float] = {}

_cache_lock = threading.Lock()

def _fetch_history(symbol: str):
    """
    Fetch 1Y historical data for a symbol.
    One network request per symbol.
    """
    ticker = yf.Ticker(symbol)
    return ticker.history(period="1y", auto_adjust=True)


def _get_history_cached(symbol: str):
    now = time.time()

    with _cache_lock:
        if symbol in _history_cache:
            if now - _history_cache_time[symbol] < CACHE_TTL:
                return _history_cache[symbol]

    hist = _fetch_history(symbol)

    with _cache_lock:
        _history_cache[symbol] = hist
        _history_cache_time[symbol] = now

    return hist


def _pct_change(first: float, last: float) -> Optional[float]:
    if first <= 0:
        return None
    return round(((last - first) / first) * 100, 2)


def compute_performance(hist) -> Dict[str, Optional[float]]:
    if hist.empty or len(hist) < 2:
        return {}

    close = hist["Close"]

    return {
        "24h": _pct_change(close.iloc[-2], close.iloc[-1]),
        "7d": _pct_change(close.iloc[-5], close.iloc[-1]) if len(close) >= 5 else None,
        "30d": _pct_change(close.iloc[-22], close.iloc[-1]) if len(close) >= 22 else None,
        "3mo": _pct_change(close.iloc[-66], close.iloc[-1]) if len(close) >= 66 else None,
        "1y": _pct_change(close.iloc[0], close.iloc[-1]),
    }



def _fetch_all_symbols(symbols: List[str]) -> List[Dict]:
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_get_history_cached, symbol): symbol
            for symbol in symbols
        }

        for future in concurrent.futures.as_completed(futures):
            symbol = futures[future]
            try:
                hist = future.result()
                perf = compute_performance(hist)

                if perf:
                    results.append({
                        "symbol": symbol,
                        "performance": perf
                    })

            except Exception as e:
                print(f"{symbol} failed: {e}")

    return results


def best_performers(period: str, limit: int = 5) -> List[Dict]:
    key = f"best:{period}:{limit}"
    now = time.time()

    if key in _result_cache and now - _result_cache_time[key] < CACHE_TTL:
        return _result_cache[key]

    data = _fetch_all_symbols(UNIVERSE)

    filtered = [
        {"symbol": d["symbol"], "change": d["performance"].get(period)}
        for d in data
        if d["performance"].get(period) is not None
    ]

    result = sorted(filtered, key=lambda x: x["change"], reverse=True)[:limit]

    _result_cache[key] = result
    _result_cache_time[key] = now

    return result


def worst_performers(period: str, limit: int = 5) -> List[Dict]:
    key = f"worst:{period}:{limit}"
    now = time.time()

    if key in _result_cache and now - _result_cache_time[key] < CACHE_TTL:
        return _result_cache[key]

    data = _fetch_all_symbols(UNIVERSE)

    filtered = [
        {"symbol": d["symbol"], "change": d["performance"].get(period)}
        for d in data
        if d["performance"].get(period) is not None
    ]

    result = sorted(filtered, key=lambda x: x["change"])[:limit]

    _result_cache[key] = result
    _result_cache_time[key] = now

    return result


def get_stock_performance(symbol: str) -> Optional[Dict]:
    try:
        hist = _get_history_cached(symbol)
        if hist.empty:
            return None

        close = hist["Close"].iloc[-1]

        return {
            "symbol": symbol.upper(),
            "current_price": round(float(close), 2),
            "performances": compute_performance(hist)
        }

    except Exception as e:
        print(f"{symbol} error: {e}")
        return None

def start_cache_warming():
    def warm():
        popular = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        for s in popular:
            _get_history_cached(s)

    t = threading.Thread(target=warm, daemon=True)
    t.start()


start_cache_warming()
