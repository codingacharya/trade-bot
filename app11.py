import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator, WilliamsRIndicator
from ta.trend import ADXIndicator, SMAIndicator

# ==================================================
# PAGE SETUP
# ==================================================
st.set_page_config(layout="wide")
st.title("📉 PUT Side Multi-Timeframe Trading Strategy (NSE Safe)")

# ==================================================
# SIDEBAR
# ==================================================
symbol = st.sidebar.text_input("Symbol", "^NSEI")
tf = st.sidebar.selectbox("Timeframe", ["2h", "10m", "2m"])

# ==================================================
# DATA FETCH (SAFE FOR NSE)
# ==================================================
@st.cache_data
def fetch_data(symbol, tf):

    def clean_columns(df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    if tf == "2h":
        df = yf.download(
            symbol, interval="15m", period="60d",
            auto_adjust=True, progress=False
        )
        df = clean_columns(df)
        df = df.resample("2H").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        })

    elif tf == "10m":
        df = yf.download(
            symbol, interval="5m", period="15d",
            auto_adjust=True, progress=False
        )
        df = clean_columns(df)
        df = df.resample("10T").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        })

    else:  # 2m
        df = yf.download(
            symbol, interval="2m", period="7d",
            auto_adjust=True, progress=False
        )
        df = clean_columns(df)

    df.dropna(inplace=True)
    return df

# ==================================================
# FETCH DATA (df IS CREATED HERE)
# ==================================================
df = fetch_data(symbol, tf)

# ==================================================
# VALIDATION
# ==================================================
MIN_BARS = 160

if df is None or df.empty or len(df) < MIN_BARS:
    st.error(f"❌ Not enough candles: {0 if df is None else len(df)} (Need ≥ {MIN_BARS})")
    st.stop()

df = df.copy()
df["Close"] = df["Close"].astype(float)

# ==================================================
# SAFE BB FUNCTION
# ==================================================
def safe_bb(series, window):
    bb = BollingerBands(series, window=window)
    return bb.bollinger_hband(), bb.bollinger_lband()

# ==================================================
# INDICATORS
# ==================================================
bb60_h, bb60_l = safe_bb(df["Close"], 60)
df["BB60_width"] = (bb60_h - bb60_l) / df["Close"]

df["RSI"] = RSIIndicator(df["Close"], 20).rsi()
df["WR"] = WilliamsRIndicator(
    df["High"], df["Low"], df["Close"], 28
).williams_r()

dmi6 = ADXIndicator(df["High"], df["Low"], df["Close"], 6)
dmi20 = ADXIndicator(df["High"], df["Low"], df["Close"], 20)

df["+DI_6"] = dmi6.adx_pos()
df["-DI_6"] = dmi6.adx_neg()
df["+DI_20"] = dmi20.adx_pos()
df["-DI_20"] = dmi20.adx_neg()

df["MA8"] = SMAIndicator(df["Close"], 8).sma_indicator()

df.dropna(inplace=True)

# ==================================================
# PUT ENTRY CONDITIONS
# ==================================================
df["PUT_ENTRY"] = (
    (df["WR"] <= -80) &
    (df["RSI"] <= 40) &
    (df["-DI_6"] >= 35) &
    (df["+DI_6"] <= 15) &
    (df["-DI_20"] >= 30) &
    (df["+DI_20"] <= 15)
)

# ==================================================
# PUT EXIT CONDITIONS
# ==================================================
df["DMI_DIFF"] = abs(df["+DI_20"] - df["-DI_20"])
df["PUT_EXIT"] = (df["DMI_DIFF"] < 10) | (df["Close"] > df["MA8"])

# ==================================================
# SIGNAL TABLE
# ==================================================
st.subheader("📊 Latest Signals")
st.dataframe(
    df[[
        "Close", "RSI", "WR",
        "+DI_6", "-DI_6",
        "+DI_20", "-DI_20",
        "PUT_ENTRY", "PUT_EXIT"
    ]].tail(15),
    use_container_width=True
)

# ==================================================
# CLEAR & PROFESSIONAL CHART
# ==================================================
st.subheader("📈 Price Chart with PUT Signals")

# Show only last N candles for clarity
DISPLAY_BARS = st.slider("Number of candles to display", 50, 300, 120)

plot_df = df.tail(DISPLAY_BARS)

fig = go.Figure()

# --- Candlestick ---
fig.add_trace(go.Candlestick(
    x=plot_df.index,
    open=plot_df["Open"],
    high=plot_df["High"],
    low=plot_df["Low"],
    close=plot_df["Close"],
    increasing_line_color="#00ff9c",
    decreasing_line_color="#ff4d4d",
    name="Price"
))

# --- MA 8 ---
fig.add_trace(go.Scatter(
    x=plot_df.index,
    y=plot_df["MA8"],
    line=dict(color="yellow", width=2),
    name="MA 8"
))

# --- PUT ENTRY (Down Arrow) ---
fig.add_trace(go.Scatter(
    x=plot_df[plot_df["PUT_ENTRY"]].index,
    y=plot_df[plot_df["PUT_ENTRY"]]["High"] * 1.002,
    mode="markers",
    marker=dict(symbol="triangle-down", color="red", size=14),
    name="PUT ENTRY"
))

# --- PUT EXIT (Up Arrow) ---
fig.add_trace(go.Scatter(
    x=plot_df[plot_df["PUT_EXIT"]].index,
    y=plot_df[plot_df["PUT_EXIT"]]["Low"] * 0.998,
    mode="markers",
    marker=dict(symbol="triangle-up", color="lime", size=14),
    name="PUT EXIT"
))

# --- Layout ---
fig.update_layout(
    template="plotly_dark",
    height=700,
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=1.02),
    margin=dict(l=20, r=20, t=40, b=20)
)

fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=True)

st.plotly_chart(fig, use_container_width=True)

# ==================================================
# STRATEGY STATUS
# ==================================================
st.subheader("🧠 Strategy Status")
latest = df.iloc[-1]

if latest["PUT_ENTRY"]:
    st.error("🔴 PUT ENTRY SIGNAL ACTIVE")
elif latest["PUT_EXIT"]:
    st.success("🟢 EXIT SIGNAL TRIGGERED")
else:
    st.info("⚪ No Active Signal")
