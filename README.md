# Live Trading Dashboard & Pine Script Strategy (Angel One SmartAPI)

An intraday trading terminal and systematic algorithmic trading engine integrating **TradingView Pine Script v6**, **Angel One SmartAPI (SmartWebSocketV2)**, and a **real-time Streamlit + Plotly 5-minute interactive dashboard**.

---

## 📌 Features

1. **TradingView Pine Script v6 Strategy**:
   - Anchored Daily VWAP, Dual EMA (9 & 21), RSI (9), ATR (14), and Volume SMA (20).
   - Intraday session timing filter (09:30 to 15:00 IST) and 15:15 IST automatic square-off.
   - Dynamic indicator-driven Stop Loss ($ATR \times 1.5$) and Target ($Risk \times 2.0$).
   - Persistent label overlay with exact priority: `BUY` -> `SELL` -> `HOLD` -> `NONE`.
   - Audio and webhook alert conditions.

2. **Python Live Strategy Engine**:
   - 100% mathematical parity with Pine Script calculations (Wilder's RMA smoothing, anchored VWAP).
   - Zero look-ahead bias: evaluations trigger on finalized 5-minute candle boundaries.
   - Conservative same-candle resolution (Stop Loss prioritized when both boundaries are hit).

3. **5-Minute Candle Aggregation Engine**:
   - Native Asia/Kolkata (`pytz`) timezone synchronization.
   - Handles cumulative broker volume by calculating interval volume from ticks.
   - Forming candle updates continuously; finalized candles dispatched to strategy listeners.

4. **Angel One SmartAPI WebSocket Feed**:
   - Automated TOTP generation via `pyotp`.
   - Full live quote WebSocket stream (`SmartWebSocketV2`) with auto-reconnect.
   - Built-in simulation fallback mode for testing outside market hours.

5. **Streamlit & Plotly Trading Terminal**:
   - Interactive candlestick chart with overlays for VWAP, EMA 9, EMA 21, and Volume.
   - Visual markers for confirmed BUY / SELL signals.
   - Real-time horizontal levels for Entry, Target, and Stop-Loss.
   - Signal cards displaying Live Unrealized P&L %, Entry Price, and Target/Stop values.
   - Historical backtesting module with performance metrics and equity curve.
   - Candle-by-candle Pine Script vs Python parity inspector.

---

## 🚀 Windows Setup & Installation

### Step 1: Open PowerShell and Navigate to Project
```powershell
cd c:\Users\ASUS\OneDrive\Desktop\VWAP_final
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Credentials
Your local `.env` has been initialized. If you ever update credentials, edit `.env`:
```ini
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_code
ANGEL_PASSWORD=your_mpin_or_password
ANGEL_TOTP_SECRET=your_base32_totp_secret
DEFAULT_EXCHANGE=NSE
DEFAULT_SYMBOL=RELIANCE-EQ
DEFAULT_TOKEN=2885
MOCK_MODE=false
```

---

## 🧪 Testing and Verification

### 1. Run the Parity Audit
Validates indicator formulas and state transitions against the Pine Script logic:
```powershell
python parity_check.py
```

### 2. Run the Full Unit Test Suite
Runs tests for candle aggregation, indicators, strategy state transitions, and exits:
```powershell
pytest -v tests/
```

---

## 🖥️ Launching the Application

### 1. High-Performance Pure HTML Local Server (Recommended)
Blazing-fast sub-second loading, in-memory RAM cache for 20 trading days, multi-timeframe switching (5m, 15m, 1h, 1d), native on-chart drawing tools (measurements, zones, eraser), and real-time tick updates:
```powershell
python server.py
```
Open your browser at **`http://localhost:8000`**.

### 2. Standalone 24/7 Terminal Daemon (Headless / No Browser)
Runs 24/7 in background terminal, evaluates 5-minute clock boundaries, and dispatches Telegram alerts without opening any browser:
```powershell
python live_runner.py
```

### 3. Legacy Streamlit Dashboard
```powershell
streamlit run app.py
```
Open at `http://localhost:8501`.

---

## 📊 Pine Script Setup in TradingView

1. Open [TradingView](https://www.tradingview.com) and open any chart (e.g. `NSE:RELIANCE`, 5-minute timeframe).
2. Open the **Pine Editor** tab at the bottom.
3. Open `tradingview_strategy.pine` from this folder, copy its contents, and paste it into the Pine Editor.
4. Click **Save** and **Add to Chart**.
5. The indicator lines, BUY/SELL signals, and the interactive status label will appear on the latest bar.
