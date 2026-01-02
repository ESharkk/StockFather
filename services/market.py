import yfinance as yf
import time
import concurrent.futures
import threading
from typing import List, Dict, Optional, Tuple
from services.universe import load_sp500


UNIVERSE = load_sp500()


_symbol_cache: Dict[str, Tuple[Optional[float], float]] = {}
_symbol_cache_ttl = 300


_result_cache: Dict[str, Dict] = {}
_RESULT_CACHE_TTL = 300


_last_request_time = 0
_MIN_REQUEST_INTERVAL = 1.0  # Increased to 1 second




def _rate_limited_request():
   global _last_request_time
   current_time = time.time()
   elapsed = current_time - _last_request_time


   if elapsed < _MIN_REQUEST_INTERVAL:
       time.sleep(_MIN_REQUEST_INTERVAL - elapsed)


   _last_request_time = time.time()




def _get_change_single(symbol: str, period: str) -> Optional[float]:
   try:
       ticker = yf.Ticker(symbol)
       _rate_limited_request()


       # FOR YFINANCE 0.2.18 - DIFFERENT PARAMETERS
       if period == "24h":
           # For 24h change, get 2 days and compare yesterday to today
           hist = ticker.history(period="2d")
       else:
           period_map = {
               "7d": "5d",  # yfinance 0.2.18 uses "5d" not "7d"
               "30d": "1mo",
               "3mo": "3mo",
               "1y": "1y"
           }
           hist = ticker.history(period=period_map.get(period, "1mo"))


       if hist.empty or len(hist) < 2:
           return None


       if period == "24h":
           if len(hist) >= 2:
               # Compare yesterday's close to today's close
               first = hist["Close"].iloc[-2]
               second = hist["Close"].iloc[-1]
           else:
               return None
       else:
           first = hist["Close"].iloc[0]
           second = hist["Close"].iloc[-1]


       if first > 0:
           return round(((second - first) / first) * 100, 2)
       return None


   except Exception as e:
       print(f"Error fetching {symbol}: {e}")
       return None




def _get_change_cached(symbol: str, period: str) -> Optional[float]:
   cache_key = f"{symbol}:{period}"
   now = time.time()


   cached = _symbol_cache.get(cache_key)
   if cached and (now - cached[1] < _symbol_cache_ttl):
       return cached[0]


   change = _get_change_single(symbol, period)
   _symbol_cache[cache_key] = (change, now)
   return change




def _get_changes_parallel(symbols: List[str], period: str, max_workers: int = 5) -> List[Dict]:
   """SLOWER but more reliable"""
   results = []


   # Process one by one with longer delays
   for symbol in symbols[:50]:  # Limit to 50 symbols
       change = _get_change_cached(symbol, period)
       if change is not None:
           results.append({"symbol": symbol, "change": change})
       time.sleep(0.5)  # Half second between requests


   return results




def best_performers(period: str, limit: int = 5) -> List[Dict]:
   result_key = f"best:{period}:{limit}"
   now = time.time()


   cached_result = _result_cache.get(result_key)
   if cached_result and (now - cached_result["timestamp"] < _RESULT_CACHE_TTL):
       return cached_result["data"]


   # Only check top 50 symbols for now
   symbols_to_check = UNIVERSE[:50]
   results = _get_changes_parallel(symbols_to_check, period)


   if not results:
       return []


   sorted_results = sorted(results, key=lambda x: x["change"], reverse=True)[:limit]


   _result_cache[result_key] = {
       "data": sorted_results,
       "timestamp": now
   }


   return sorted_results




def worst_performers(period: str, limit: int = 5) -> List[Dict]:
   result_key = f"worst:{period}:{limit}"
   now = time.time()


   cached_result = _result_cache.get(result_key)
   if cached_result and (now - cached_result["timestamp"] < _RESULT_CACHE_TTL):
       return cached_result["data"]


   symbols_to_check = UNIVERSE[:50]
   results = _get_changes_parallel(symbols_to_check, period)


   if not results:
       return []


   sorted_results = sorted(results, key=lambda x: x["change"])[:limit]


   _result_cache[result_key] = {
       "data": sorted_results,
       "timestamp": now
   }


   return sorted_results




def cached_best_performers(period: str, limit: int = 5) -> List[Dict]:
   return best_performers(period, limit)




def cached_worst_performers(period: str, limit: int = 5) -> List[Dict]:
   return worst_performers(period, limit)




def get_stock_performance(symbol: str) -> Optional[Dict]:
   try:
       ticker = yf.Ticker(symbol)
       _rate_limited_request()


       # DON'T use .info - it causes 429 errors
       # Instead, get price from history
       hist = ticker.history(period="2d")
       if hist.empty:
           return None


       current_price = hist["Close"].iloc[-1]


       performances = {}
       periods = ["24h", "7d", "30d", "3mo", "1y"]


       for period in periods:
           change = _get_change_cached(symbol, period)
           performances[period] = change


       return {
           "symbol": symbol.upper(),
           "name": symbol,  # Can't get real name without .info
           "current_price": current_price,
           "performances": performances
       }
   except Exception as e:
       print(f"Error getting stock performance for {symbol}: {e}")
       return None




def start_cache_warming():
   """Simplified warming - just a few symbols"""


   def warm_task():
       popular_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
       periods = ["24h", "7d", "30d"]


       for symbol in popular_symbols:
           for period in periods:
               _get_change_cached(symbol, period)
               time.sleep(2)  # Long delay to avoid bans


   thread = threading.Thread(target=warm_task, daemon=True)
   thread.start()
   return thread




_warming_thread = start_cache_warming()
