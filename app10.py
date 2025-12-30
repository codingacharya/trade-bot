import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="NIFTY 50 Intraday Dashboard", layout="wide")
st.title("📊 NIFTY 50 Intraday Trading Dashboard")

# =====================================================
# SIDEBAR MENU
# =====================================================
menu = st.sidebar.radio(
    "📌 Analysis Menu",
    [
        "📈 Price & Trend",
        "📊 Bollinger Bands",
        "📉 RSI",
        "🔁 MACD",
        "🔊 Volume",
        "🎯 Confidence Score",
        "🧾 Final Verdict"
    ]
)

# =====================================================
# NIFTY 50 SYMBOLS
# =====================================================
NIFTY_50 = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "AXISBANK": "AXISBANK.NS",
    "ITC": "ITC.NS",
    "LT": "LT.NS",
    "BHARTIARTL": "BHARTIARTL.NS"
}

stock = st.sidebar.selectbox("Select NIFTY 50 Stock", list(NIFTY_50.keys()))
symbol = NIFTY_50[stock]

interval = st.sidebar.selectbox(
    "Intraday Timeframe",
    ["5m", "15m", "30m"],
    index=1
)

# =====================================================
# DATA LOADER
# =====================================================
@st.cache_data
def load_data(symbol, interval):
    return yf.download(
        symbol,
        period="5d",
        interval=interval,
        progress=False
    )

df = load_data(symbol, interval)

if df.empty or len(df) < 50:
    st.error("❌ Data kurang bro, market lagi sepi atau symbol salah")
    st.stop()

# =====================================================
# FIX yfinance MULTI-COLUMN BUG
# =====================================================
if isinstance(df["Close"], pd.DataFrame):
    df["Close"] = df["Close"].iloc[:, 0]

# =====================================================
# INDICATORS (ALGORITHMS)
# =====================================================

# EMA
df["EMA9"] = df["Close"].ewm(span=9).mean()
df["EMA21"] = df["Close"].ewm(span=21).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()

# Bollinger Bands
bb_mid = df["Close"].rolling(20).mean()
bb_std = df["Close"].rolling(20).std()
df["BB_MID"] = bb_mid
df["BB_UP"] = bb_mid + 2 * bb_std
df["BB_LOW"] = bb_mid - 2 * bb_std

# RSI
delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9).mean()

# =====================================================
# SAFE SCALARS
# =====================================================
latest = df.iloc[-1]

close = float(latest["Close"])
ema9 = float(latest["EMA9"])
ema21 = float(latest["EMA21"])
ema50 = float(latest["EMA50"])
rsi = float(latest["RSI"])
macd = float(latest["MACD"])
signal = float(latest["Signal"])
volume = float(latest["Volume"])
avg_volume = float(df["Volume"].rolling(20).mean().iloc[-1])
bb_mid_val = float(latest["BB_MID"])

# =====================================================
# CONFIDENCE SCORE ALGORITHM
# =====================================================
bullish = 0
checks = 6

if close > ema21 and ema21 > ema50: bullish += 1
if close > ema9: bullish += 1
if rsi > 55: bullish += 1
if macd > signal: bullish += 1
if volume > avg_volume: bullish += 1
if close > bb_mid_val: bullish += 1

confidence = int((bullish / checks) * 100)

# =====================================================
# MENU PAGES
# =====================================================
if menu == "📈 Price & Trend":
    st.subheader(f"{stock} – Price & Trend")
    fig = go.Figure()
    fig.add_candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )
    fig.add_scatter(x=df.index, y=df["EMA9"], name="EMA 9")
    fig.add_scatter(x=df.index, y=df["EMA21"], name="EMA 21")
    fig.add_scatter(x=df.index, y=df["EMA50"], name="EMA 50")
    fig.update_layout(height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

elif menu == "📊 Bollinger Bands":
    st.subheader("Bollinger Bands")
    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df["BB_UP"], name="Upper Band")
    fig.add_scatter(x=df.index, y=df["BB_LOW"], name="Lower Band")
    fig.add_scatter(x=df.index, y=df["Close"], name="Price")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "📉 RSI":
    st.subheader("RSI Analysis")
    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df["RSI"])
    fig.add_hline(y=70, line_dash="dash")
    fig.add_hline(y=30, line_dash="dash")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "🔁 MACD":
    st.subheader("MACD Analysis")
    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df["MACD"], name="MACD")
    fig.add_scatter(x=df.index, y=df["Signal"], name="Signal")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "🔊 Volume":
    st.subheader("Volume Analysis")
    fig = go.Figure()
    fig.add_bar(x=df.index, y=df["Volume"])
    st.metric("Current Volume", int(volume))
    st.metric("Avg Volume", int(avg_volume))
    st.plotly_chart(fig, use_container_width=True)

elif menu == "🎯 Confidence Score":
    st.subheader("Confidence Score")
    st.markdown(f"## 🎯 {confidence}%")
    st.progress(confidence / 100)

elif menu == "🧾 Final Verdict":
    if confidence >= 70:
        verdict = "🟢 BUY (Bullish)"
    elif confidence <= 35:
        verdict = "🔴 SELL (Bearish)"
    else:
        verdict = "🟡 HOLD (Sideways)"

    st.subheader("Final Intraday Verdict")
    st.markdown(f"## {verdict}")
    st.markdown(f"### Confidence: {confidence}%")

st.success("✅ Dashboard siap dipakai — gas trading tapi tetap pakai SL 😄")
