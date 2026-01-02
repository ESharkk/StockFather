import json
from pathlib import Path


CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
SP500_FILE = CACHE_DIR / "sp500.json"


def load_sp500():
    if SP500_FILE.exists() and SP500_FILE.stat().st_size > 0:
        with open(SP500_FILE, 'r') as f:
            symbols = json.load(f)
            cleaned_symbols = [s.replace('$', '') for s in symbols]
            return cleaned_symbols


    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    import requests
    from io import StringIO

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    import pandas as pd
    df = pd.read_html(StringIO(response.text))[0]

    symbols = df["Symbol"].str.replace(r'[\$\^\.]', '', regex=True).tolist()

    with open(SP500_FILE, 'w') as f:
        json.dump(symbols, f, indent=2)

    print(f"Successfully loaded {len(symbols)} symbols")
    return symbols
