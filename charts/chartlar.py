import matplotlib.pyplot as plt
from io import BytesIO
import yfinance as yf
import time


class ChartService:
   def __init__(self):
       plt.style.use('seaborn-v0_8-darkgrid')
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
           data = ticker.history(period="1mo", interval="1d")
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


   def generate_price_chart(self, symbol: str, period: str = "30d"):
       """Generate price chart with caching - consistent candlestick style"""
       chart_key = f"chart:{symbol}:{period}:price"
       now = time.time()


       # Check chart cache first
       if chart_key in self._chart_cache:
           if now - self._chart_cache[chart_key]["timestamp"] < self.chart_ttl:
               return self._chart_cache[chart_key]["image"]


       # Get data (cached or fresh)
       data = self._get_cached_data(symbol, period)


       if data.empty or len(data) < 2:
           return None


       # Create figure
       fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8),
                                      gridspec_kw={'height_ratios': [3, 1]})


       # Set style with better contrast
       plt.style.use('default')
       fig.patch.set_facecolor('#0f0f23')
       ax1.set_facecolor('#0f0f23')
       ax2.set_facecolor('#0f0f23')


       # Determine bar width based on number of data points
       num_points = len(data)
       if num_points <= 10:
           bar_width = 0.6
           wick_width = 1.5
       elif num_points <= 30:
           bar_width = 0.4
           wick_width = 1.0
       elif num_points <= 90:
           bar_width = 0.3
           wick_width = 0.8
       else:
           bar_width = 0.2
           wick_width = 0.6


       # Plot candlestick chart for ALL timeframes
       for idx in range(len(data)):
           row = data.iloc[idx]
           # Determine color based on price movement
           if row['Close'] >= row['Open']:
               color = '#00d4aa'  # Green for bullish
               body_bottom = row['Open']
               body_height = row['Close'] - row['Open']
           else:
               color = '#ff6b6b'  # Red for bearish
               body_bottom = row['Close']
               body_height = row['Open'] - row['Close']


           # Draw candle body (rectangle)
           if body_height > 0:
               rect = plt.Rectangle(
                   (idx - bar_width / 2, body_bottom),
                   bar_width, body_height,
                   color=color, alpha=0.8, linewidth=0
               )
               ax1.add_patch(rect)


           # Draw wick (high-low line)
           ax1.plot([idx, idx], [row['Low'], row['High']],
                    color=color, linewidth=wick_width, alpha=0.8)


       # Set x-axis ticks and labels
       ax1.set_xticks(range(len(data)))


       # Format x-axis labels based on timeframe
       labels = [''] * len(data)  # Start with all empty labels


       if period == "1d":
           # For intraday: show only the beginning of each hour
           last_hour_shown = None
           for i, date in enumerate(data.index):
               current_hour = date.hour
               minute = date.minute


               # Show label for the first data point of each hour
               # OR if it's the first/last data point
               if i == 0 or i == len(data) - 1:
                   labels[i] = date.strftime('%H:%M')
                   last_hour_shown = current_hour
               elif current_hour != last_hour_shown and minute < 30:  # Beginning of hour
                   labels[i] = f"{current_hour:02d}:00"
                   last_hour_shown = current_hour


           rotation = 45


       elif period == "7d":
           # For 7 days: show abbreviated day names with dates
           last_day_shown = None
           for i, date in enumerate(data.index):
               current_day = date.strftime('%Y-%m-%d')


               if i == 0 or i == len(data) - 1:
                   day_abbr = date.strftime('%a')[:2]  # Mo, Tu, We, etc.
                   day_num = date.strftime('%d')
                   labels[i] = f"{day_abbr}\n{day_num}"
                   last_day_shown = current_day
               elif current_day != last_day_shown:
                   day_abbr = date.strftime('%a')[:2]
                   day_num = date.strftime('%d')
                   labels[i] = f"{day_abbr}\n{day_num}"
                   last_day_shown = current_day


           rotation = 45


       elif period == "30d":
           # For 30 days: show date for first of each week
           last_week_shown = None
           for i, date in enumerate(data.index):
               week_num = date.isocalendar()[1]  # Week number


               if i == 0 or i == len(data) - 1:
                   labels[i] = date.strftime('%m/%d')
                   last_week_shown = week_num
               elif week_num != last_week_shown:
                   labels[i] = date.strftime('%m/%d')
                   last_week_shown = week_num


           rotation = 45


       elif period == "3mo":
           # For 3 months: show month names
           current_month = None
           for i, date in enumerate(data.index):
               month = date.strftime('%b')


               if i == 0 or i == len(data) - 1:
                   labels[i] = month
                   current_month = month
               elif month != current_month:
                   labels[i] = month
                   current_month = month


           rotation = 0


       elif period == "1y":
           # For 1 year: show month names
           current_month = None
           month_count = 0
           for i, date in enumerate(data.index):
               month = date.strftime('%b')


               if i == 0 or i == len(data) - 1:
                   labels[i] = month
                   current_month = month
                   month_count = 1
               elif month != current_month:
                   month_count += 1
                   if month_count % 2 == 0:  # Show every other month
                       labels[i] = month
                   current_month = month


           rotation = 0


       # Set light-colored labels for dark background
       ax1.set_xticklabels(labels, rotation=rotation, ha='right', color='#cccccc', fontsize=9)
       ax1.tick_params(axis='x', colors='#cccccc')
       ax1.tick_params(axis='y', colors='#cccccc')


       # Set title and grid with light colors
       ax1.set_title(f'{symbol} - {period.upper()} Price Chart',
                     fontsize=14, fontweight='bold', pad=20, color='#ffffff')
       ax1.grid(True, alpha=0.2, linestyle='--', color='#555555')
       ax1.set_ylabel('Price ($)', color='#cccccc')


       # Plot volume as area chart
       volume_colors = []
       for idx in range(len(data)):
           row = data.iloc[idx]
           volume_colors.append('#00d4aa' if row['Close'] >= row['Open'] else '#ff6b6b')


       # Create volume bars
       x_positions = range(len(data))
       ax2.bar(x_positions, data['Volume'], color=volume_colors,
               alpha=0.7, width=bar_width * 1.2, align='center')


       # Format volume x-axis with same labels
       ax2.set_xticks(x_positions)
       ax2.set_xticklabels(labels, rotation=rotation, ha='right', color='#cccccc', fontsize=9)
       ax2.tick_params(axis='x', colors='#cccccc')
       ax2.tick_params(axis='y', colors='#cccccc')


       ax2.set_title('Volume', fontsize=10, color='#ffffff', pad=10)
       ax2.set_ylabel('Volume', color='#cccccc')
       ax2.grid(True, alpha=0.2, linestyle='--', color='#555555')


       # Adjust layout
       plt.tight_layout()
       plt.subplots_adjust(bottom=0.15)


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
                   self.generate_price_chart(symbol, period)
                   print(f"Pre-cached {symbol} {period}")
               except:
                   pass




# Create a global instance
chart_service = ChartService()
