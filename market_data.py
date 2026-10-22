"""
Datos de mercado para el panel de McDuck (banner, índices y gráficos).

Por qué NO se usa Alpha Vantage aquí:
  el plan gratuito permite ~25 consultas al día. Un banner con 12 acciones
  las gastaría en dos recargas. Para el panel se usa Yahoo Finance (yfinance,
  sin clave, varias acciones en una sola llamada). Alpha Vantage queda para
  las herramientas del agente y como respaldo del histórico.

Cada función devuelve (datos, fuente). `fuente` es "yahoo", "alphavantage"
o "demo". Los datos "demo" son inventados y la interfaz los marca como tales:
nunca se muestran como si fueran reales.
"""

import os
import random
import zlib

import pandas as pd
import requests

POPULARES = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
             "TSLA", "JPM", "V", "WMT", "KO", "DIS"]

INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
    "^VIX": "VIX (volatilidad)",
}

# Precios base aproximados, solo para generar datos de demostración.
_BASE_DEMO = {
    "AAPL": 230, "MSFT": 440, "NVDA": 130, "AMZN": 190, "GOOGL": 175,
    "META": 560, "TSLA": 250, "JPM": 215, "V": 280, "WMT": 80, "KO": 68,
    "DIS": 95, "^GSPC": 5800, "^IXIC": 18200, "^DJI": 42000, "^VIX": 16,
}


# ----------------------------------------------------------------------
# Datos de demostración (deterministas por símbolo)
# ----------------------------------------------------------------------
def _demo_history(symbol: str, days: int = 260) -> pd.DataFrame:
    rng = random.Random(zlib.crc32(symbol.encode()))
    base = _BASE_DEMO.get(symbol, 50 + rng.random() * 200)
    fechas = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    cierre = base * 0.85
    filas = []
    for f in fechas:
        apertura = cierre * (1 + rng.uniform(-0.006, 0.006))
        cierre = max(1.0, apertura * (1 + rng.gauss(0.0006, 0.013)))
        alto = max(apertura, cierre) * (1 + rng.uniform(0, 0.008))
        bajo = min(apertura, cierre) * (1 - rng.uniform(0, 0.008))
        filas.append((f, apertura, alto, bajo, cierre, int(rng.uniform(2e7, 9e7))))
    df = pd.DataFrame(filas, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    return df.set_index("Date")


def _quotes_from_histories(symbols, histories) -> list[dict]:
    out = []
    for s in symbols:
        closes = histories[s]["Close"].dropna()
        if len(closes) < 2:
            continue
        price, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
        out.append({
            "symbol": s,
            "price": price,
            "change": price - prev,
            "pct": (price / prev - 1) * 100,
            "spark": [float(x) for x in closes.tail(30)],
        })
    return out


# ----------------------------------------------------------------------
# Cotizaciones (banner, índices, tabla de variaciones)
# ----------------------------------------------------------------------
def get_quotes(symbols) -> tuple[list[dict], str]:
    symbols = list(symbols)
    try:
        import yfinance as yf
        data = yf.download(symbols, period="1mo", interval="1d",
                           group_by="ticker", auto_adjust=False,
                           progress=False, threads=True, timeout=10)
        histories = {}
        for s in symbols:
            try:
                histories[s] = data[s].dropna(how="all")
            except KeyError:
                continue
        quotes = _quotes_from_histories(list(histories), histories)
        if quotes:
            return quotes, "yahoo"
    except Exception as e:  # red caída, Yahoo limitando, paquete ausente...
        print(f"[market_data] Yahoo no disponible para cotizaciones: {e}")

    demo = {s: _demo_history(s, 40) for s in symbols}
    return _quotes_from_histories(symbols, demo), "demo"


# ----------------------------------------------------------------------
# Histórico OHLCV de una acción (gráfico principal)
# ----------------------------------------------------------------------
def _history_yahoo(symbol: str):
    import yfinance as yf
    df = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=False)
    if df is None or df.empty:
        return None
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def _history_alpha_vantage(symbol: str):
    key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not key:
        return None
    r = requests.get("https://www.alphavantage.co/query", timeout=20, params={
        "function": "TIME_SERIES_DAILY", "symbol": symbol,
        "outputsize": "compact", "apikey": key})
    serie = r.json().get("Time Series (Daily)")
    if not serie:
        return None
    df = pd.DataFrame.from_dict(serie, orient="index").astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns={"1. open": "Open", "2. high": "High", "3. low": "Low",
                            "4. close": "Close", "5. volume": "Volume"})
    return df.sort_index()[["Open", "High", "Low", "Close", "Volume"]]


def get_history(symbol: str) -> tuple[pd.DataFrame, str]:
    symbol = symbol.upper().strip()
    try:
        df = _history_yahoo(symbol)
        if df is not None and len(df) > 5:
            return df, "yahoo"
    except Exception as e:
        print(f"[market_data] Yahoo no disponible para {symbol}: {e}")
    try:
        df = _history_alpha_vantage(symbol)
        if df is not None and len(df) > 5:
            return df, "alphavantage"
    except Exception as e:
        print(f"[market_data] Alpha Vantage no disponible para {symbol}: {e}")
    return _demo_history(symbol), "demo"


# ----------------------------------------------------------------------
# Formato de números
# ----------------------------------------------------------------------
def fmt_big(valor) -> str:
    """1234567890 -> '1.23 MM'. T = billones, MM = miles de millones, M = millones."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    for limite, sufijo in ((1e12, " T"), (1e9, " MM"), (1e6, " M")):
        if abs(v) >= limite:
            return f"{v / limite:,.2f}{sufijo}"
    return f"{v:,.0f}"


def fmt_num(valor, decimales=2, sufijo="") -> str:
    try:
        return f"{float(valor):,.{decimales}f}{sufijo}"
    except (TypeError, ValueError):
        return "—"
