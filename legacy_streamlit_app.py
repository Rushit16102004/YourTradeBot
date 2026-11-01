"""
Streamlit Live Terminal with real-time Plotly charts, ZFTF indicator signals, Angel One integration,
and Telegram notifications for NIFTY 50.
Features:
- 20 Days of Candles loaded from 1st Priority In-Memory RAM Cache (with CSV fallback).
- Multi-timeframe selector: 5 min, 15 min, 1 Hour, 1 Day.
- Real-time tick-by-tick updates (replacing 5-minute delayed wait).
- On-Chart Interactive Drawing Tools (Measurement & trend lines, Zone rectangles & squares, Erase).
- Full-screen 920px trading desk layout.
"""
import time
import os
import logging
import threading
from datetime import datetime
import pytz
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import SmartAPIConfig, StrategyConfig, TelegramConfig
from chart import create_trading_chart, create_accessible_chart, CHART_CONFIG
from background_engine import BackgroundTradingEngine

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

# Streamlit Page Config - Expansive Wide Layout
st.set_page_config(
    page_title="NIFTY 50 Live Trading Terminal (20-Day Full Pro)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #2962ff;
        margin-bottom: 10px;
    }
    .signal-buy {
        background-color: #1b5e20;
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        font-size: 20px;
    }
    .signal-sell {
        background-color: #b71c1c;
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        font-size: 20px;
    }
    .signal-hold {
        background-color: #e65100;
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        font-size: 20px;
    }
    .signal-none {
        background-color: #424242;
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        font-size: 20px;
    }
    /* Toolbar info banner */
    .draw-tip {
        background: #1e222d;
        border: 1px solid #2962ff;
        border-radius: 6px;
        padding: 6px 12px;
        color: #90caf9;
        font-size: 13px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Background Engine (Persistent Singleton)
def init_system():
    if "initialized" not in st.session_state:
        api_cfg = SmartAPIConfig()
        strat_cfg = StrategyConfig()
        tg_cfg = TelegramConfig()

        bg_engine = BackgroundTradingEngine.get_instance(api_cfg, strat_cfg, tg_cfg)
        bg_engine.start()

        st.session_state.api_cfg = api_cfg
        st.session_state.strat_cfg = strat_cfg
        st.session_state.tg_cfg = tg_cfg
        st.session_state.bg_engine = bg_engine
        st.session_state.initialized = True

        # Send Telegram startup alert on initial run
        if bg_engine.notifier.is_configured:
            threading.Thread(target=bg_engine.notifier.send_startup_alert, daemon=True).start()


init_system()

# Ensure background engine is running
bg_engine = BackgroundTradingEngine.get_instance(
    st.session_state.get("api_cfg"),
    st.session_state.get("strat_cfg"),
    st.session_state.get("tg_cfg"),
)
bg_engine.start()

# Sidebar Configuration
st.sidebar.title("Trading Control Panel")
mode_str = "🟢 Angel One LIVE" if bg_engine.is_authed else "🟡 Simulation / Mock Feed"
st.sidebar.info(f"Feed Status: **{mode_str}**")

# Exclusively dedicated to NIFTY 50
exchange = "NSE"
symbol = "NIFTY 50"
token = "99926000"

st.sidebar.markdown("""
<div style="background-color: #0d47a1; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
    <div style="font-size: 18px; font-weight: bold;">🇮🇳 NIFTY 50 INDEX</div>
    <div style="font-size: 12px; color: #bbdefb; margin-top: 4px;">Exchange: NSE | Token: 99926000</div>
    <div style="font-size: 11px; color: #90caf9; margin-top: 2px;">20-Day High-Speed RAM Engine</div>
</div>
""", unsafe_allow_html=True)

# ----------------- TIMEFRAME SELECTION (5m, 15m, 1H, 1D) -----------------
st.sidebar.subheader("⏱️ Candle Timeframe")
selected_timeframe = st.sidebar.selectbox(
    "Select Chart Timeframe",
    ["5 min", "15 min", "1 Hour", "1 Day"],
    index=0,
    help="Dynamically resampled from the 20-day in-memory RAM base dataset."
)

# 1st Priority Cache Memory Status Badge
st.sidebar.markdown("""
<div style="background-color: #004d40; color: #80cbc4; padding: 9px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold; margin-bottom: 10px; border: 1px solid #00bfa5;">
    🧠 20-Day RAM Cache: Active (Zero Lag)
</div>
""", unsafe_allow_html=True)

# ----------------- TELEGRAM STATUS (DIRECT IN CODE) -----------------
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="background-color: #1b5e20; color: white; padding: 10px; border-radius: 6px; text-align: center; font-size: 13px; font-weight: bold; margin-bottom: 10px;">
    📱 Telegram Alerts: Active
</div>
""", unsafe_allow_html=True)

col_b1, col_b2, col_b3 = st.sidebar.columns(3)
with col_b1:
    if st.button("🚀 Start Msg", use_container_width=True, help="Test startup alert"):
        ok, msg = bg_engine.notifier.send_startup_alert()
        if ok:
            st.sidebar.success("✅ Startup sent!")
        else:
            st.sidebar.error(f"❌ {msg}")

with col_b2:
    if st.button("🧪 Test Msg", use_container_width=True, help="Test general bot connection"):
        ok, test_msg = bg_engine.notifier.send_test_alert()
        if ok:
            st.sidebar.success("✅ Test sent!")
        else:
            st.sidebar.error(f"❌ {test_msg}")

with col_b3:
    if st.button("⏰ 3:10 EOD", use_container_width=True, help="Test 3:10 PM EOD alert"):
        snapshot = bg_engine.get_snapshot(selected_timeframe)
        ok, test_msg = bg_engine.notifier.send_eod_alert(
            price=snapshot["price"],
            in_position=snapshot["state"].in_position,
            alert_time=datetime.now(IST),
        )
        if ok:
            st.sidebar.success("✅ EOD sent!")
        else:
            st.sidebar.error(f"❌ {test_msg}")

# ----------------- STRATEGY PARAMETERS SIDEBAR -----------------
st.sidebar.markdown("---")
st.sidebar.subheader("ZFTF Strategy Parameters")
w_val = st.sidebar.number_input("Rolling Window", 5, 100, int(bg_engine.strat_cfg.window))
z_val = st.sidebar.slider("Z Entry Threshold", 0.5, 4.0, float(bg_engine.strat_cfg.z_threshold), 0.1)
se_val = st.sidebar.number_input("Slope Entry Threshold", -0.05, 0.05, float(bg_engine.strat_cfg.slope_entry), 0.0005, format="%.4f")
sx_val = st.sidebar.number_input("Slope Exit Threshold", -0.05, 0.05, float(bg_engine.strat_cfg.slope_exit), 0.0005, format="%.4f")

# Update parameters if changed
if (w_val != bg_engine.strat_cfg.window or
    z_val != bg_engine.strat_cfg.z_threshold or
    se_val != bg_engine.strat_cfg.slope_entry or
    sx_val != bg_engine.strat_cfg.slope_exit):
    bg_engine.strat_cfg.window = w_val
    bg_engine.strat_cfg.z_threshold = z_val
    bg_engine.strat_cfg.slope_entry = se_val
    bg_engine.strat_cfg.slope_exit = sx_val
    bg_engine.sync_and_evaluate(force_alert=False)

st.sidebar.markdown("---")
realtime_tick_sync = st.sidebar.checkbox(
    "⚡ Real-Time Tick Update (Live)",
    value=True,
    help="Updates price, forming candle wick, indicators, and signals live on every tick without waiting 5 minutes."
)

# Fetch latest thread-safe snapshot from background engine for selected timeframe
snapshot = bg_engine.get_snapshot(timeframe=selected_timeframe)
df_ind = snapshot["df"]
current_ltp = snapshot["price"]
state = snapshot["state"]
signal_history = snapshot["signal_history"]
now_time = datetime.now(IST)

# 3:10 PM EOD Square-Off Notification Banner
is_eod_time = (now_time.hour == 15 and now_time.minute >= 10) or now_time.hour > 15
if is_eod_time:
    st.markdown("""
    <div style="background-color: #b71c1c; color: white; padding: 12px 18px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; font-size: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
        <div>⏰ <b>3:10 PM EOD SQUARE-OFF:</b> Market closes at 3:30 PM. EXIT ALL TRADES AS EOD.</div>
        <div style="background: rgba(0,0,0,0.3); padding: 4px 10px; border-radius: 4px; font-size: 12px; letter-spacing: 0.5px;">EOD CUTOFF</div>
    </div>
    """, unsafe_allow_html=True)

# TOP STATUS BAR (Real-Time Tick Status)
col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
with col_s1:
    st.metric("Instrument", f"{symbol}")
with col_s2:
    st.metric("Live Market Price (LTP)", f"₹{current_ltp:.2f}")
with col_s3:
    st.metric("Timeframe", f"{selected_timeframe} (20-Day)")
with col_s4:
    st.metric("Candle Count", f"{len(df_ind)} Bars (RAM Cache)")
with col_s5:
    st.metric("Position Mode", state.position_type)

st.markdown("---")

# SIGNAL PANEL (FOCUS ON SIGNAL, ESSENTIAL PRICE, TARGET & STOP)
col_sig, col_price, col_pnl, col_entry, col_tgt, col_stp = st.columns([2.5, 2, 1.8, 1.8, 1.8, 1.8])

with col_sig:
    st.markdown("#### TradingView Signal Status")
    if state.signal == 1:
        st.markdown('<div class="signal-buy">BUY</div>', unsafe_allow_html=True)
    elif state.signal == -1:
        st.markdown('<div class="signal-sell">SELL</div>', unsafe_allow_html=True)
    elif state.in_position:
        st.markdown('<div class="signal-hold">HOLD</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal-none">NONE</div>', unsafe_allow_html=True)

with col_price:
    st.metric("Live Traded Price", f"₹{current_ltp:.2f}")

with col_pnl:
    pnl_val = f"{state.live_pnl_pct:+.2f}%" if state.live_pnl_pct is not None else "NA"
    st.metric("Unrealized P&L", pnl_val)

with col_entry:
    ep_str = f"₹{state.entry_price:.2f}" if state.entry_price else "NA"
    st.metric("Entry Price", ep_str)

with col_tgt:
    tgt_str = f"₹{state.target_price:.2f}" if state.target_price else "NA"
    st.metric("Target (+6%)", tgt_str)

with col_stp:
    stp_str = f"₹{state.stop_loss:.2f}" if state.stop_loss else "NA"
    st.metric("Stop Loss (-3%)", stp_str)

st.markdown("---")

# TOOLBAR: DATE DISPLAY, REFRESH CANDLES TILL CURRENT, CHART STYLE
col_act1, col_act2, col_act3 = st.columns([2.5, 2, 2.5])
with col_act1:
    chart_mode = st.radio(
        "Chart Style",
        ["🕯️ Detailed Candlestick", "📊 Simple Accessible Price Chart"],
        horizontal=True,
        label_visibility="collapsed"
    )
with col_act2:
    today_date_str = datetime.now(IST).strftime("%A, %d-%b-%Y")
    st.markdown(f"<div style='padding-top: 6px; font-weight: bold; color: #90caf9;'>📅 <b>{today_date_str}</b></div>", unsafe_allow_html=True)

with col_act3:
    if st.button("🔄 Sync 20-Day Data Now", use_container_width=True):
        bg_engine.sync_and_evaluate(force_alert=False)
        st.rerun()

# Drawing tools tip for the user
st.markdown("""
<div class="draw-tip">
    🛠️ <b>On-Chart Drawing Tools Active (Top Right of Chart):</b> 
    Click <b>Draw Line</b> (📏) for trendlines & measurements | Click <b>Draw Rectangle</b> (🔲) to mark supply/demand zones & boxes | Click <b>Erase</b> (🗑️) to remove.
</div>
""", unsafe_allow_html=True)

# DASHBOARD TABS (EXCLUSIVELY GRAPH & SIGNALS)
tab_chart, tab_hist = st.tabs([
    f"📈 Live {selected_timeframe} Chart (20 Days Fullscreen)", "📜 Confirmed Signals Log"
])

with tab_chart:
    if "Simple" in chart_mode:
        fig = create_accessible_chart(df_ind, state, signal_history, symbol=symbol, timeframe=selected_timeframe)
    else:
        fig = create_trading_chart(df_ind, state, signal_history, symbol=symbol, timeframe=selected_timeframe, config=bg_engine.strat_cfg)
    
    # Render with full-screen container width and interactive drawing tools toolbar
    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

    if len(df_ind) > 0:
        last_row = df_ind.iloc[-1]
        ic1, ic2, ic3, ic4 = st.columns(4)
        ic1.metric("Rolling Mean (SMA 20)", f"₹{last_row.get('mean', 0):.2f}")
        ic2.metric("Z-Score", f"{last_row.get('z', 0):.2f}")
        ic3.metric("Linreg Slope", f"{last_row.get('slope', 0):.4f}")
        ic4.metric("Std Dev (σ)", f"{last_row.get('std', 0):.2f}")

with tab_hist:
    st.subheader(f"Confirmed Strategy Signals Log ({selected_timeframe} - 20 Days)")
    if signal_history:
        df_sig = pd.DataFrame(signal_history)
        st.dataframe(df_sig, use_container_width=True)
    else:
        st.info("No signals generated in the selected 20-day range yet. Signals trigger when Z > 2.0 and Slope > 0.001.")

# ----------------- REAL-TIME TICK-BY-TICK SYNC + INSTANT TAB FOCUS -----------------
# 1. Background Python thread evaluates candles & alerts Telegram 24/7.
# 2. When looking at the terminal, updates tick-by-tick every 2 seconds.
# 3. When user switches back from another tab, visibilitychange triggers an INSTANT update!
if realtime_tick_sync:
    components.html(
        """
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background-color: #1a2332; border: 1px solid #1e88e5; border-radius: 6px;
                    padding: 8px 14px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;">
            <div style="color: #90caf9; font-size: 13px; font-weight: 500;">
                ⚡ <b>Real-Time Tick Engine:</b> Live updates on every market tick. 20-day candles cached in RAM memory.
            </div>
            <div style="color: #00e676; font-size: 13px; font-weight: bold; background: #003318; padding: 4px 10px; border-radius: 4px; border: 1px solid #00e676;">
                ● LIVE TICK FEED ACTIVE
            </div>
        </div>
        <script>
            (function() {
                function triggerRefresh() {
                    try {
                        var buttons = window.parent.document.querySelectorAll('button');
                        for (var i = 0; i < buttons.length; i++) {
                            if (buttons[i].innerText.includes("Sync 20-Day Data")) {
                                buttons[i].click();
                                break;
                            }
                        }
                    } catch (e) {
                        console.error("Tick sync error:", e);
                    }
                }

                // Instant sync the moment user switches back to this browser tab!
                document.addEventListener('visibilitychange', function() {
                    if (document.visibilityState === 'visible') {
                        triggerRefresh();
                    }
                });
                window.addEventListener('focus', function() {
                    triggerRefresh();
                });

                // Real-time tick update every 2 seconds while active
                setInterval(function() {
                    if (document.visibilityState === 'visible') {
                        triggerRefresh();
                    }
                }, 2000);
            })();
        </script>
        """,
        height=52,
    )

# Entry point enabling both `python app.py` and `streamlit run app.py`
if __name__ == "__main__":
    if not st.runtime.exists():
        import sys
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", "app.py"]
        sys.exit(stcli.main())