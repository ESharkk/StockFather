from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Best Performers", callback_data="best")],
        [InlineKeyboardButton("📉 Worst Performers", callback_data="worst")],
        [InlineKeyboardButton("🔍 Search and Charts", callback_data="search")],
    ])

def search_prompt_menu():
    """Menu shown when asking user to enter stock symbol"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Home", callback_data="menu")]
    ])


def search_stock_menu(symbol):
    """Menu after showing stock performance"""
    clean_symbol = symbol.replace('$', '') if '$' in symbol else symbol

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Price and Vol", callback_data=f"chartselect:price:{clean_symbol}"),
            InlineKeyboardButton("📈 RSI, MACD, ATR", callback_data=f"chartselect:indicators:{clean_symbol}"),
        ],
        [
            InlineKeyboardButton("🔍 Search Another", callback_data="search"),
            InlineKeyboardButton("🏠 Home", callback_data="menu"),
        ]
    ])


def stock_result_menu(symbol, has_chart=True):
    """Menu after showing stock performance - same as above"""
    buttons = []

    if has_chart:
        buttons.append([
            InlineKeyboardButton("📊 Price and Vol", callback_data=f"chartselect:price:{symbol}"),
            InlineKeyboardButton("📈 RSI, MACD, ATR", callback_data=f"chartselect:indicators:{symbol}"),
        ])

    buttons.append([
        InlineKeyboardButton("🔍 Search Another", callback_data="search"),
        InlineKeyboardButton("🏠 Home", callback_data="menu"),
    ])

    return InlineKeyboardMarkup(buttons)


def chart_period_menu(symbol, chart_type="price"):
    """Select chart timeframe - MUST include chart_type"""
    chart_type_text = "Price & Volume" if chart_type == "price" else "RSI, MACD, ATR"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1D", callback_data=f"chart:{chart_type}:{symbol}:1d"),
            InlineKeyboardButton("7D", callback_data=f"chart:{chart_type}:{symbol}:7d"),
            InlineKeyboardButton("30D", callback_data=f"chart:{chart_type}:{symbol}:30d"),
        ],
        [
            InlineKeyboardButton("3M", callback_data=f"chart:{chart_type}:{symbol}:3mo"),
            InlineKeyboardButton("1Y", callback_data=f"chart:{chart_type}:{symbol}:1y"),
        ],
        [
            InlineKeyboardButton("◀️ Back", callback_data=f"stock_back:{symbol}"),
            InlineKeyboardButton("🏠 Home", callback_data="menu"),
        ]
    ])

def timeframe_menu(prefix):
    """Select timeframe (today/7d/30d)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Today", callback_data=f"{prefix}_24h"),
            InlineKeyboardButton("7d", callback_data=f"{prefix}_7d"),
            InlineKeyboardButton("30d", callback_data=f"{prefix}_30d"),
        ],
        [
            InlineKeyboardButton("3m", callback_data=f"{prefix}_3mo"),
            InlineKeyboardButton("1y", callback_data=f"{prefix}_1y"),
        ],
        [InlineKeyboardButton("🏠 Home", callback_data="menu")]
    ])

def limit_menu(prefix, period):
    """Select how many stocks to show"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5 stocks", callback_data=f"{prefix}_{period}_5"),
            InlineKeyboardButton("10 stocks", callback_data=f"{prefix}_{period}_10"),
        ],
        [
            InlineKeyboardButton("20 stocks", callback_data=f"{prefix}_{period}_20"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="menu"),
            InlineKeyboardButton("🏠 Home", callback_data="menu"),
        ]
    ])

def results_menu(prefix, period, limit):
    """Menu after showing results"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Change Time", callback_data=prefix),
            InlineKeyboardButton("🏠 Home", callback_data="menu"),
        ],
    ])
