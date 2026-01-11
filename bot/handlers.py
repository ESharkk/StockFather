import asyncio
import concurrent.futures
import json
import time
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import (
    chart_period_menu,
    limit_menu,
    main_menu,
    results_menu,
    search_prompt_menu,
    search_stock_menu,
    stock_result_menu,
    timeframe_menu,
)
from charts.chartlar import chart_service
from services.market import best_performers, get_stock_performance, worst_performers

# Load S&P 500 symbols for validation
SP500_FILE = Path("cache") / "sp500.json"
if SP500_FILE.exists():
    with open(SP500_FILE, "r") as f:
        VALID_SYMBOLS = set(json.load(f))
else:
    VALID_SYMBOLS = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Stock Advisor Bot\n\nWelcome! Use the buttons to explore the market.\n⚠️ Not financial advice.",
        reply_markup=main_menu(),
    )


async def run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, func, *args, **kwargs)


async def show_adaptive_progress(q, task_description, task_func, *args, **kwargs):
    start_time = time.time()
    message = await q.edit_message_text(f"⚡ {task_description}")

    time_task = asyncio.create_task(update_time_display(message, task_description, start_time))

    result = await task_func(*args, **kwargs)
    elapsed = time.time() - start_time

    time_task.cancel()

    await message.edit_text(f"✅ {task_description} ({elapsed:.1f}s)")
    await asyncio.sleep(0.3)

    return result, message


async def update_time_display(message, task_description, start_time):
    icons = ["⚡", "⏳", "🔄"]

    while True:
        await asyncio.sleep(1)

        elapsed = time.time() - start_time
        seconds = int(elapsed)

        if seconds < 2:
            icon = icons[0]
        elif seconds < 5:
            icon = icons[1]
        elif seconds < 10:
            icon = icons[2]

        if seconds < 60:
            time_display = f"{seconds}s"
        else:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            time_display = f"{minutes}m {remaining_seconds}s"

        await message.edit_text(f"{icon} {task_description} ({time_display})")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    def is_photo_message(message):
        """Check if message contains a photo"""
        return message and (hasattr(message, "photo") and message.photo)

    if data == "menu":
        if is_photo_message(q.message):  # FIXED
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text="📊 Stock Advisor Bot\n\nSelect an option:",
                reply_markup=main_menu(),
            )
        else:
            await q.edit_message_text(
                "📊 Stock Advisor Bot\n\nSelect an option:", reply_markup=main_menu()
            )

    elif data == "search":
        if is_photo_message(q.message):  # FIXED
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text="🔍 Stock Search\n\nEnter a stock symbol:",
                reply_markup=search_prompt_menu(),
            )
        else:
            await q.edit_message_text(
                "🔍 Stock Search\n\nEnter a stock symbol:", reply_markup=search_prompt_menu()
            )
        context.user_data["awaiting_stock"] = True

    elif data in ["best", "worst"]:
        action = "Best" if data == "best" else "Worst"
        if is_photo_message(q.message):  # FIXED
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"📈 {action} Performers\n\nSelect timeframe:",
                reply_markup=timeframe_menu(data),
            )
        else:
            await q.edit_message_text(
                f"📈 {action} Performers\n\nSelect timeframe:", reply_markup=timeframe_menu(data)
            )

    elif data.count("_") == 1 and data.endswith(("_24h", "_7d", "_30d", "_3mo", "_1y")):
        prefix, period = data.split("_")
        action = "Best" if prefix == "best" else "Worst"
        period_text = {
            "24h": "Today",
            "7d": "7 Days",
            "30d": "30 Days",
            "3mo": "3 Months",
            "1y": "1 Year",
        }[period]

        if is_photo_message(q.message):  # FIXED
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"📈 {action} Performers - {period_text}\n\nHow many stocks to show?",
                reply_markup=limit_menu(prefix, period),
            )
        else:
            await q.edit_message_text(
                f"📈 {action} Performers - {period_text}\n\nHow many stocks to show?",
                reply_markup=limit_menu(prefix, period),
            )

    elif data.count("_") == 2:
        prefix, period, limit_str = data.split("_")
        limit = int(limit_str)

        period_text = {
            "24h": "Today",
            "7d": "7 Days",
            "30d": "30 Days",
            "3mo": "3 Months",
            "1y": "1 Year",
        }[period]

        async def fetch_performers():
            if prefix == "best":
                results = await run_in_thread(best_performers, period, limit)
                return results, "📈 Top"
            else:
                results = await run_in_thread(worst_performers, period, limit)
                return results, "📉 Bottom"

        (results, title), progress_msg = await show_adaptive_progress(
            q, f"Fetching {period_text} performers", fetch_performers
        )

        if not results:
            await progress_msg.edit_text(
                f"❌ No data available for {period_text} period.",
                reply_markup=timeframe_menu(prefix),
            )
            return

        lines = []
        for i, item in enumerate(results, 1):
            change_icon = "🟢" if item["change"] >= 0 else "🔴"
            lines.append(f"{i}. {change_icon} {item['symbol']}: {item['change']:+}%")

        text = f"{title} {limit} Performers ({period_text})\n\n" + "\n".join(lines)

        await progress_msg.edit_text(text, reply_markup=results_menu(prefix, period, limit))

    # Chart type selection
    # Chart type selection
    elif data.startswith("chartselect:"):
        # chartselect:price:symbol or chartselect:indicators:symbol
        parts = data.split(":")
        chart_type = parts[1]
        symbol = parts[2]

        chart_type_text = "Price & Volume" if chart_type == "price" else "RSI, MACD, ATR"

        if is_photo_message(q.message):
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"📊 {symbol} - {chart_type_text}\n\nSelect timeframe:",
                reply_markup=chart_period_menu(symbol, chart_type),
            )
        else:
            await q.edit_message_text(
                f"📊 {symbol} - {chart_type_text}\n\nSelect timeframe:",
                reply_markup=chart_period_menu(symbol, chart_type),
            )

    # Chart generation (ALL timeframes including 30d)
    elif data.startswith("chart:") and len(data.split(":")) == 4:
        # chart:type:symbol:period
        parts = data.split(":")
        chart_type = parts[1]
        symbol = parts[2]
        period = parts[3]

        # Show loading
        loading_msg = await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"📈 Generating {chart_type} chart for {symbol} ({period.upper()})...",
        )

        # Generate chart
        if chart_type == "price":
            image_bytes = chart_service.generate_price_volume_chart(symbol, period)
            chart_title = f"{symbol} - Price & Volume ({period.upper()})"
        else:  # indicators
            image_bytes = chart_service.generate_indicators_chart(symbol, period)
            chart_title = f"{symbol} - RSI, MACD, ATR ({period.upper()})"

        if image_bytes:
            await loading_msg.delete()
            await context.bot.send_photo(
                chat_id=q.message.chat_id,
                photo=image_bytes,
                caption=chart_title,
                reply_markup=chart_period_menu(symbol, chart_type),
            )
            if not is_photo_message(q.message):
                await q.message.delete()
        else:
            await loading_msg.edit_text(
                text="❌ Could not generate chart. Please try again.",
                reply_markup=stock_result_menu(symbol, has_chart=False),
            )

    elif data.startswith("stock_back:"):
        symbol = data.split(":")[1]

        stock_data = get_stock_performance(symbol)

        if not stock_data:
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"❌ Could not find data for {symbol}",
                reply_markup=main_menu(),
            )
            return

        lines = []
        lines.append(f"<b>{stock_data['symbol']}</b>")

        if stock_data["current_price"]:
            lines.append(f"Current Price: ${stock_data['current_price']:.2f}")

        lines.append("")

        performances = stock_data["performances"]
        for p, change in performances.items():
            if change is not None:
                p_text = {
                    "24h": "24 Hours",
                    "7d": "7 Days",
                    "30d": "30 Days",
                    "3mo": "3 Months",
                    "1y": "1 Year",
                }[p]
                change_icon = "🟢" if change >= 0 else "🔴"
                lines.append(f"{change_icon} {p_text}: {change:+}%")
            else:
                p_text = {
                    "24h": "24 Hours",
                    "7d": "7 Days",
                    "30d": "30 Days",
                    "3mo": "3 Months",
                    "1y": "1 Year",
                }[p]
                lines.append(f"⭕ {p_text}: No data")

        text = "\n".join(lines)

        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=search_stock_menu(symbol),
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages for stock search"""
    if context.user_data.get("awaiting_stock"):
        symbol = update.message.text.upper().strip()

        # Quick validation using S&P 500 list
        if VALID_SYMBOLS and symbol not in VALID_SYMBOLS:
            await update.message.reply_text(
                f"❌ {symbol} not found in S&P 500. Try symbols like AAPL, MSFT, TSLA.",
                reply_markup=main_menu(),
            )
            context.user_data["awaiting_stock"] = False
            return

        stock_data = get_stock_performance(symbol)

        if not stock_data:
            await update.message.reply_text(
                f"❌ Could not find data for {symbol}.", reply_markup=main_menu()
            )
        else:
            lines = []
            lines.append(f"<b>{stock_data['symbol']}</b>")

            if stock_data["current_price"]:
                lines.append(f"Current Price: ${stock_data['current_price']:.2f}")

            lines.append("")

            performances = stock_data["performances"]
            for period, change in performances.items():
                if change is not None:
                    period_text = {
                        "24h": "24 Hours",
                        "7d": "7 Days",
                        "30d": "30 Days",
                        "3mo": "3 Months",
                        "1y": "1 Year",
                    }[period]
                    change_icon = "🟢" if change >= 0 else "🔴"
                    lines.append(f"{change_icon} {period_text}: {change:+}%")
                else:
                    period_text = {
                        "24h": "24 Hours",
                        "7d": "7 Days",
                        "30d": "30 Days",
                        "3mo": "3 Months",
                        "1y": "1 Year",
                    }[period]
                    lines.append(f"⭕ {period_text}: No data")

            text = "\n".join(lines)

            await update.message.reply_text(
                text, parse_mode="HTML", reply_markup=search_stock_menu(symbol)
            )

        context.user_data["awaiting_stock"] = False
