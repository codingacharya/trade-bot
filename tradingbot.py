# tradingbot.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Trading Bot", layout="wide")

# -------------------------
# Sidebar Inputs
# -------------------------
st.sidebar.header("Settings")
symbol = st.sidebar.text_input("Symbol", value="AAPL")
interval = st.sidebar.selectbox("Interval", ["1m","5m","15m","30m","1h","1d"], index=5)

period_map = {"1m":"7d","5m":"60d","15m":"60d","30m":"60d","1h":"730d","1d":"5y"}
period = period_map.get(interval, "60d")

# Indicator parameters
macd_fast = st.sidebar.number_input("MACD fast EMA", 1, 100, 12)
macd_slow = st.sidebar.number_input("MACD slow EMA", 1, 200, 26)
macd_signal = st.sidebar.number_input("MACD signal EMA", 1, 50, 9)

bb_period = st.sidebar.number_input("BB period", 1, 100, 20)
bb_std = st.sidebar.number_input("BB stddev", 0.1, 5.0, 2.0, 0.1)

dpo_period = st.sidebar.number_input("DPO period", 2, 100, 20)
adx_period = st.sidebar.number_input("ADX (DMI) period", 2, 50, 14)

cvo_short = st.sidebar.number_input("CVO short EMA", 1, 100, 14)
cvo_long = st.sidebar.number_input("CVO long EMA", 1, 200, 28)

fib_lookback = st.sidebar.number_input("Fibonacci lookback", 2, 500, 50)

refresh = st.sidebar.button("Refresh Data")

# -------------------------
# Fetch Data
# -------------------------
@st.cache_data(ttl=60)
def fetch_data(sym, per, inter):
    df = yf.download(sym, period=per, interval=inter, threads=False, progress=False)
    if df.empty:
        return pd.DataFrame()
    
    # Keep required columns
    df = df.loc[:, ["Open","High","Low","Close","Volume"]].copy()
    
    # Flatten MultiIndex columns if any
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    
    # Ensure 1-D numpy arrays for each column
    for col in df.columns:
        arr = np.array(df[col])
        if arr.ndim > 1:
            df[col] = pd.Series(arr.flatten(), index=df.index)
        else:
            df[col] = pd.Series(arr, index=df.index)
    
    return df

df = fetch_data(symbol, period, interval)
if df.empty:
    st.error(f"No data for {symbol} ({interval})")
    st.stop()

# -------------------------
# Indicator Functions
# -------------------------
def add_bollinger(df, period=20, num_std=2.0):
    ma = df["Close"].rolling(period).mean()
    std = df["Close"].rolling(period).std()
    upper = ma + std*num_std
    lower = ma - std*num_std
    return upper, ma, lower

def add_macd(df, fast=12, slow=26, signal=9):
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist

def add_dpo(df, period=20):
    shift = int(period/2 + 1)
    sma = df["Close"].rolling(window=period).mean()
    return df["Close"].shift(shift) - sma

def add_cvo(df, short=14, long=28):
    vol_short = df["Volume"].ewm(span=short, adjust=False).mean()
    vol_long = df["Volume"].ewm(span=long, adjust=False).mean()
    with np.errstate(divide='ignore', invalid='ignore'):
        cvo = 100.0 * (vol_short - vol_long)/vol_long.replace(0, np.nan)
    return cvo, vol_short, vol_long

def add_adx(df, period=14):
    high = np.array(df["High"]).astype(float).flatten()
    low = np.array(df["Low"]).astype(float).flatten()
    close = np.array(df["Close"]).astype(float).flatten()
    if len(close)<2:
        n = len(df)
        return (pd.Series([np.nan]*n,index=df.index),
                pd.Series([np.nan]*n,index=df.index),
                pd.Series([np.nan]*n,index=df.index))
    tr1 = high[1:]-low[1:]
    tr2 = np.abs(high[1:]-close[:-1])
    tr3 = np.abs(low[1:]-close[:-1])
    tr = np.max(np.vstack([tr1,tr2,tr3]),axis=0).flatten()
    up = high[1:]-high[:-1]
    down = low[:-1]-low[1:]
    plus_dm = np.where((up>down)&(up>0),up,0.0).flatten()
    minus_dm = np.where((down>up)&(down>0),down,0.0).flatten()
    tr_smooth = pd.Series(tr).rolling(period).sum()
    plus_smooth = pd.Series(plus_dm).rolling(period).sum()
    minus_smooth = pd.Series(minus_dm).rolling(period).sum()
    plus_di = 100*(plus_smooth/tr_smooth.replace(0,np.nan))
    minus_di = 100*(minus_smooth/tr_smooth.replace(0,np.nan))
    dx = 100*np.abs(plus_di-minus_di)/(plus_di+minus_di).replace(0,np.nan)
    adx = dx.rolling(period).mean()
    pad_len = len(df.index)-len(adx)
    plus_di_full = pd.Series([np.nan]*pad_len + list(plus_di.values),index=df.index)
    minus_di_full = pd.Series([np.nan]*pad_len + list(minus_di.values),index=df.index)
    adx_full = pd.Series([np.nan]*pad_len + list(adx.values),index=df.index)
    return plus_di_full, minus_di_full, adx_full

def fibonacci_levels(df, lookback=50):
    if len(df)<2: return {}
    window = df.tail(int(lookback))
    high, low = window["High"].max(), window["Low"].min()
    diff = high-low
    return {
        "Swing High": high,
        "Swing Low": low,
        "0.0": high,
        "0.236": high-0.236*diff,
        "0.382": high-0.382*diff,
        "0.5": high-0.5*diff,
        "0.618": high-0.618*diff,
        "0.786": high-0.786*diff,
        "1.0": low
    }

# -------------------------
# Compute Indicators
# -------------------------
df_ind = df.copy()

df_ind["BB_upper"], df_ind["BB_mid"], df_ind["BB_lower"] = add_bollinger(df_ind, bb_period, bb_std)
df_ind["MACD"], df_ind["MACD_SIGNAL"], df_ind["MACD_HIST"] = add_macd(df_ind, macd_fast, macd_slow, macd_signal)
df_ind["DPO"] = add_dpo(df_ind, dpo_period)
df_ind["CVO"], df_ind["VOL_EMA_SHORT"], df_ind["VOL_EMA_LONG"] = add_cvo(df_ind, cvo_short, cvo_long)
df_ind["PLUS_DI"], df_ind["MINUS_DI"], df_ind["ADX"] = add_adx(df_ind, adx_period)
fib_levels = fibonacci_levels(df_ind, fib_lookback)

# Flatten & Fix Column Names
df_ind.columns = [str(col).strip() for col in df_ind.columns]
for col in df_ind.columns:
    arr = np.array(df_ind[col])
    if arr.ndim > 1:
        df_ind[col] = pd.Series(arr.flatten(), index=df_ind.index)
    else:
        df_ind[col] = pd.Series(arr, index=df_ind.index)

# -------------------------
# Streamlit Charts & Display
# -------------------------
st.title(f"{symbol} — DPO / DMI / BB / CVO / MACD / Fibonacci")
st.markdown(f"Interval = **{interval}**, Period requested = **{period}**")

col_chart, col_side = st.columns([2,1])

with col_chart:
    st.subheader("Price Chart + Bollinger Bands")
    chart_df = pd.DataFrame({
        "Close": df_ind["Close"].to_numpy().flatten(),
        "BB_upper": df_ind["BB_upper"].to_numpy().flatten(),
        "BB_mid": df_ind["BB_mid"].to_numpy().flatten(),
        "BB_lower": df_ind["BB_lower"].to_numpy().flatten(),
    }, index=df_ind.index).dropna(axis=1, how="all")
    st.line_chart(chart_df.tail(500))

    st.subheader("MACD")
    st.line_chart(df_ind[["MACD","MACD_SIGNAL"]].tail(300))
    st.bar_chart(df_ind["MACD_HIST"].fillna(0).tail(300))

    st.subheader("DPO")
    st.line_chart(df_ind["DPO"].fillna(0).tail(300))

    st.subheader("CVO")
    st.line_chart(df_ind["CVO"].fillna(0).tail(300))

    st.subheader("DMI / ADX")
    st.line_chart(df_ind[["PLUS_DI","MINUS_DI","ADX"]].fillna(0).tail(300))

with col_side:
    st.subheader("Latest Indicator Values")
    latest = df_ind.iloc[-1]
    latest_dict = {name: latest[name] for name in df_ind.columns if name not in ["Open","High","Low","Volume"]}
    st.table(pd.DataFrame.from_dict(latest_dict, orient="index", columns=["Value"]))

    st.subheader(f"Fibonacci Levels (last {fib_lookback} bars)")
    if fib_levels:
        st.table(pd.DataFrame.from_dict(fib_levels, orient="index", columns=["Level"]))
    else:
        st.write("Not enough data for Fibonacci levels.")

st.subheader("Recent Raw Data (tail)")
st.dataframe(df_ind.tail(10))

# Refresh
if refresh:
    fetch_data.clear()
    st.experimental_rerun()
