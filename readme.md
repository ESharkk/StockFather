StockFather 📊
Stock Market Analysis Telegram Bot

⚠️ Disclaimer
Educational purposes only. Not financial advice.

🚀 Quick Start
```bash
# 1. Clone & setup


git clone https://github.com/yourusername/StockFather.git
cd StockFather
python -m venv venv

# 2. Activate (Windows)
venv\Scripts\activate
# 2. Activate (Mac/Linux)
source venv/bin/activate

# 3. Install & configure
pip install -r requirements.txt
cp .env
# Edit .env with your Telegram Bot Token

# 4. Run
python main.py


``` 
📦 Features
Real-time Charts: Candlestick charts (1D, 7D, 30D, 3M, 1Y)

Market Analysis: Top/Bottom S&P 500 performers

Stock Search: Individual stock performance

Fast & Cached: Parallel processing + intelligent caching

Dark Theme: Professional chart styling

🔧 Requirements
Python 3.10+

Telegram Bot Token (from @BotFather)


## 📁 Project Structure
- **StockFather/**
  - **bot/**
    - `handlers.py` - Message and button handlers
    - `keyboards.py` - Inline keyboards
    - `__init__.py`
  - **services/**
    - `market.py` - Stock data and caching
    - `universe.py` - S&P 500 symbols loader
    - `__init__.py`
  - **charts/**
    - `chartlar.py` - Candlestick chart generator
    - `__init__.py`
  - **cache/** - Auto-generated cache (gitignored)
  - `main.py` - Application entry point
  - `requirements.txt` - Python dependencies
  - `.env` - Environment variables
  - `.gitignore` - Git ignore rules
  - `README.md` - This file

