import yfinance as yf
import time

print("Testing Yahoo Finance...")
time.sleep(2)

ticker = yf.Ticker("AAPL")
hist = ticker.history(period="1d", interval="1h")

if not hist.empty:
    print(f"✓ Yahoo Finance WORKS! Got {len(hist)} rows")
    print(f"  AAPL: ${hist['Close'].iloc[-1]:.2f}")
else:
    print("✗ Still blocked")