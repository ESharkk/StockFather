import matplotlib.pyplot as plt
from io import BytesIO
import yfinance as yf
import time
import pandas as pd
from datetime import datetime


class ChartService:
   def __init__(self):
       self._data_cache = {}
       self._chart_cache = {}
       self.data_ttl = 300
       self.chart_ttl = 900
       # Pre-cache popular stocks
       self.popular_symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "NFLX"]


   def _get_cached_data(self, symbol: str, period: str):
       """Cache raw stock data (most reused component)"""
       key = f"data:{symbol}:{period}"
       now = time.time()


       if key in self._data_cache:
           if now - self._data_cache[key]["timestamp"] < self.data_ttl:
               return self._data_cache[key]["data"]


       # Fetch new data
       ticker = yf.Ticker(symbol)


       if period == "1d":
           # Intraday - 5min intervals
           data = ticker.history(period="1d", interval="5m")
       elif period == "7d":
           data = ticker.history(period="7d", interval="1h")
       elif period == "30d":
           data = ticker.history(period="1mo", interval="1h")
       elif period == "3mo":
           data = ticker.history(period="3mo", interval="1d")
       elif period == "1y":
           data = ticker.history(period="1y", interval="1wk")
       else:
           data = ticker.history(period="1mo", interval="1d")


       # Cache it
       self._data_cache[key] = {
           "data": data,
           "timestamp": now
       }


       return data

   def _get_bar_widths(self, num_points):
       """Helper to determine bar width based on number of points"""
       if num_points <= 10:
           return 0.6, 1.5
       elif num_points <= 30:
           return 0.4, 1.0
       elif num_points <= 90:
           return 0.3, 0.8
       else:
           return 0.2, 0.6

   def _generate_labels(self, data, period):
       """Generate x-axis labels with European date format"""
       labels = [''] * len(data)
       rotation = 45

       if period == "1d":
           # For intraday: show only the beginning of each hour
           last_hour_shown = None
           for i, date in enumerate(data.index):
               current_hour = date.hour
               minute = date.minute

               if i == 0 or i == len(data) - 1:
                   labels[i] = date.strftime('%H:%M')
                   last_hour_shown = current_hour
               elif current_hour != last_hour_shown and minute < 30:
                   labels[i] = f"{current_hour:02d}:00"
                   last_hour_shown = current_hour

       elif period == "7d":
           # For 7 days: show abbreviated day names with European dates (DD/MM)
           last_day_shown = None
           for i, date in enumerate(data.index):
               current_day = date.strftime('%Y-%m-%d')

               if i == 0 or i == len(data) - 1:
                   day_abbr = date.strftime('%a')[:2]
                   day_european = date.strftime('%d/%m')
                   labels[i] = f"{day_abbr}\n{day_european}"
                   last_day_shown = current_day
               elif current_day != last_day_shown:
                   day_abbr = date.strftime('%a')[:2]
                   day_european = date.strftime('%d/%m')
                   labels[i] = f"{day_abbr}\n{day_european}"
                   last_day_shown = current_day

       elif period == "30d":
           # For 30 days: show European date (DD/MM) for first of each week
           last_week_shown = None
           for i, date in enumerate(data.index):
               week_num = date.isocalendar()[1]

               if i == 0 or i == len(data) - 1:
                   labels[i] = date.strftime('%d/%m')
                   last_week_shown = week_num
               elif week_num != last_week_shown:
                   labels[i] = date.strftime('%d/%m')
                   last_week_shown = week_num

       elif period == "3mo":
           # For 3 months: show European format (DD/MM) for month beginnings
           current_month = None
           for i, date in enumerate(data.index):
               month = date.strftime('%b')

               if i == 0 or i == len(data) - 1:
                   labels[i] = date.strftime('%d/%m')
                   current_month = month
               elif month != current_month:
                   labels[i] = date.strftime('%d/%m')
                   current_month = month

       elif period == "1y":
           # For 1 year: show European format (DD/MM) for every other month
           current_month = None
           month_count = 0
           for i, date in enumerate(data.index):
               month = date.strftime('%b')

               if i == 0 or i == len(data) - 1:
                   labels[i] = date.strftime('%d/%m')
                   current_month = month
                   month_count = 1
               elif month != current_month:
                   month_count += 1
                   if month_count % 2 == 0:
                       labels[i] = date.strftime('%d/%m')
                   current_month = month

       return labels, rotation


   def add_technical_indicators(self, data):
       """Add technical indicators with consistent colors"""
       # --- Color Scheme ---
       COLORS = {
           'bullish': '#00d4aa',  # Green for bullish
           'bearish': '#ff6b6b',  # Red for bearish
           'neutral': '#a29bfe',  # Purple for neutral/indicators
           'signal': '#fab1a0',  # Peach for signal lines
           'volume': '#74b9ff',  # Blue for volume
           'sma': '#f1c40f',  # Yellow for SMA
           'atr': '#ffeaa7',  # Light yellow for ATR
           'background': '#0f0f23',  # Dark background
           'text': '#cccccc',  # Light text
           'grid': '#555555',  # Grid lines
           'overbought': '#ff6b6b',  # Red for overbought
           'oversold': '#00d4aa'  # Green for oversold
       }

       # --- RSI (Relative Strength Index) ---
       delta = data['Close'].diff()
       gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
       loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
       rs = gain / loss
       data['RSI'] = 100 - (100 / (1 + rs))

       # --- MACD (Moving Average Convergence Divergence) ---
       exp1 = data['Close'].ewm(span=12, adjust=False).mean()
       exp2 = data['Close'].ewm(span=26, adjust=False).mean()
       data['MACD'] = exp1 - exp2
       data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
       data['MACD_Hist'] = data['MACD'] - data['MACD_Signal']

       # --- ATR (Average True Range) ---
       high_low = data['High'] - data['Low']
       high_close = abs(data['High'] - data['Close'].shift())
       low_close = abs(data['Low'] - data['Close'].shift())
       ranges = pd.concat([high_low, high_close, low_close], axis=1)
       true_range = ranges.max(axis=1)
       data['ATR'] = true_range.rolling(window=14).mean()

       return data, COLORS

   def generate_price_volume_chart(self, symbol: str, period: str = "30d"):
       """Generate ONLY price and volume chart"""
       chart_key = f"chart:{symbol}:{period}:price_volume"
       now = time.time()

       # Check chart cache first
       if chart_key in self._chart_cache:
           if now - self._chart_cache[chart_key]["timestamp"] < self.chart_ttl:
               return self._chart_cache[chart_key]["image"]

       # Get data
       data = self._get_cached_data(symbol, period)
       if data.empty or len(data) < 2:
           return None

       data, COLORS = self.add_technical_indicators(data)

       # Create ONLY 2 subplots: price and volume
       fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8),
                                      gridspec_kw={'height_ratios': [3, 1]})

       # Set consistent style
       plt.style.use('default')
       fig.patch.set_facecolor(COLORS['background'])

       # Style both axes
       for ax in [ax1, ax2]:
           ax.set_facecolor(COLORS['background'])
           ax.tick_params(axis='x', colors=COLORS['text'])
           ax.tick_params(axis='y', colors=COLORS['text'])
           ax.grid(True, alpha=0.2, linestyle='--', color=COLORS['grid'])

       # --- Price Chart (ax1) ---
       # Add SMA if enough data
       if len(data) > 20:
           data['SMA20'] = data['Close'].rolling(window=20).mean()
           ax1.plot(range(len(data)), data['SMA20'], color=COLORS['sma'],
                    linewidth=1.5, label='SMA 20', alpha=0.9)

       # Determine bar width
       num_points = len(data)
       bar_width, wick_width = self._get_bar_widths(num_points)

       # Plot candlestick chart
       for idx in range(len(data)):
           row = data.iloc[idx]
           color = COLORS['bullish'] if row['Close'] >= row['Open'] else COLORS['bearish']

           if row['Close'] >= row['Open']:
               body_bottom = row['Open']
               body_height = row['Close'] - row['Open']
           else:
               body_bottom = row['Close']
               body_height = row['Open'] - row['Close']

           # Draw candle body
           if body_height > 0:
               rect = plt.Rectangle(
                   (idx - bar_width / 2, body_bottom),
                   bar_width, body_height,
                   color=color, alpha=0.8, linewidth=0
               )
               ax1.add_patch(rect)

           # Draw wick
           ax1.plot([idx, idx], [row['Low'], row['High']],
                    color=color, linewidth=wick_width, alpha=0.8)

       # Add price stats
       last_price = data['Close'].iloc[-1]
       change = ((last_price - data['Open'].iloc[0]) / data['Open'].iloc[0]) * 100
       stats_text = f"Price: ${last_price:.2f} | Change: {change:+.2f}%"

       ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes,
                verticalalignment='top', color='white', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='#1e1e3f', alpha=0.5))

       ax1.set_title(f'{symbol} - Price & Volume ({period.upper()})',
                     fontsize=12, fontweight='bold', pad=15, color='#ffffff')
       ax1.set_ylabel('Price ($)', color=COLORS['text'], fontsize=9)

       # --- Volume Chart (ax2) ---
       volume_colors = []
       for idx in range(len(data)):
           row = data.iloc[idx]
           volume_colors.append(COLORS['bullish'] if row['Close'] >= row['Open'] else COLORS['bearish'])

       x_positions = range(len(data))
       ax2.bar(x_positions, data['Volume'], color=volume_colors,
               alpha=0.7, width=bar_width * 1.2, align='center')

       ax2.set_ylabel('Volume', color=COLORS['text'], fontsize=9)

       # --- X-axis Labels ---
       labels, rotation = self._generate_labels(data, period)

       # Set ticks and labels for both axes
       for ax in [ax1, ax2]:
           ax.set_xticks(range(len(data)))
           ax.set_xticklabels(labels, rotation=rotation, ha='right', color=COLORS['text'], fontsize=8)

       # Final layout
       plt.tight_layout()

       # Convert to bytes
       buf = BytesIO()
       plt.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                   facecolor=fig.get_facecolor(), edgecolor='none')
       plt.close(fig)
       buf.seek(0)
       image_bytes = buf.getvalue()

       # Cache the chart
       self._chart_cache[chart_key] = {
           "image": image_bytes,
           "timestamp": now
       }

       return image_bytes

   def generate_indicators_chart(self, symbol: str, period: str = "30d"):
       """Generate ONLY RSI, MACD, and ATR charts"""
       chart_key = f"chart:{symbol}:{period}:indicators"
       now = time.time()

       # Check chart cache first
       if chart_key in self._chart_cache:
           if now - self._chart_cache[chart_key]["timestamp"] < self.chart_ttl:
               return self._chart_cache[chart_key]["image"]

       # Get data
       data = self._get_cached_data(symbol, period)
       if data.empty or len(data) < 2:
           return None

       data, COLORS = self.add_technical_indicators(data)

       # Create 3 subplots for indicators
       fig, (ax_rsi, ax_macd, ax_atr) = plt.subplots(3, 1, figsize=(10, 10),
                                                     gridspec_kw={'height_ratios': [1, 1, 1]})

       # Set consistent style
       plt.style.use('default')
       fig.patch.set_facecolor(COLORS['background'])

       # Style all axes
       axes = [ax_rsi, ax_macd, ax_atr]
       for ax in axes:
           ax.set_facecolor(COLORS['background'])
           ax.tick_params(axis='x', colors=COLORS['text'])
           ax.tick_params(axis='y', colors=COLORS['text'])
           ax.grid(True, alpha=0.2, linestyle='--', color=COLORS['grid'])

       # --- RSI Chart ---
       ax_rsi.plot(range(len(data)), data['RSI'], color=COLORS['neutral'], linewidth=1.5)
       ax_rsi.axhline(70, color=COLORS['overbought'], linestyle='--', alpha=0.3)
       ax_rsi.axhline(30, color=COLORS['oversold'], linestyle='--', alpha=0.3)
       ax_rsi.set_ylabel('RSI', color=COLORS['text'], fontsize=9)
       ax_rsi.set_ylim(0, 100)
       ax_rsi.set_title(f'{symbol} - Technical Indicators ({period.upper()})',
                        fontsize=12, fontweight='bold', pad=15, color='#ffffff')

       # --- MACD Chart ---
       ax_macd.plot(range(len(data)), data['MACD'], color=COLORS['neutral'], linewidth=1.2)
       ax_macd.plot(range(len(data)), data['MACD_Signal'], color=COLORS['signal'], linewidth=1.2)

       # Histogram
       colors = [COLORS['bullish'] if x > 0 else COLORS['bearish'] for x in data['MACD_Hist']]
       ax_macd.bar(range(len(data)), data['MACD_Hist'], color=colors, alpha=0.5)
       ax_macd.set_ylabel('MACD', color=COLORS['text'], fontsize=9)

       # --- ATR Chart ---
       ax_atr.plot(range(len(data)), data['ATR'], color=COLORS['atr'], linewidth=1.5)
       ax_atr.set_ylabel('ATR ($)', color=COLORS['text'], fontsize=9)

       # --- X-axis Labels ---
       labels, rotation = self._generate_labels(data, period)

       # Set ticks and labels for all axes
       for ax in axes:
           ax.set_xticks(range(len(data)))
           ax.set_xticklabels(labels, rotation=rotation, ha='right', color=COLORS['text'], fontsize=8)

       # Final layout
       plt.tight_layout()

       # Convert to bytes
       buf = BytesIO()
       plt.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                   facecolor=fig.get_facecolor(), edgecolor='none')
       plt.close(fig)
       buf.seek(0)
       image_bytes = buf.getvalue()

       # Cache the chart
       self._chart_cache[chart_key] = {
           "image": image_bytes,
           "timestamp": now
       }

       return image_bytes




   def pre_cache_popular(self):
       """Pre-generate charts for popular stocks during idle time"""
       periods = ["1d", "7d", "30d"]
       for symbol in self.popular_symbols[:3]:  # Top 3 only
           for period in periods:
               try:
                   self.generate_price_volume_chart(symbol, period)
                   print(f"Pre-cached {symbol} {period}")
               except:
                   pass




# Create a global instance
chart_service = ChartService()
