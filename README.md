# 📈 NIFTY 50 Pro Terminal & AI Strategy Copilot

> **An advanced, institutional-grade intraday trading terminal and systematic algorithmic platform for NIFTY 50.**

🌐 **Live Website Link**: [**https://yourtradebot.duckdns.org**](https://yourtradebot.duckdns.org) *(Mirror: `http://130.210.26.32`)*

---

## 🌟 Platform Overview

**NIFTY 50 Pro Terminal** combines TradingView-grade interactive charting with systematic quantitative strategies and a real-time **Multi-Agent AI Copilot**. Built for intraday traders, scalpers, and institutional analysts, the platform delivers zero-latency market visualization, dynamic support and resistance detection, and automated Telegram alerts.

---

## 🚀 Key Features

### 1. 📊 TradingView-Grade Interactive Pro Charting
- **Multi-Timeframe Architecture**: Seamlessly switch between **5-Minute**, **15-Minute**, **1-Hour**, and **Daily (1D)** timeframes.
- **Institutional Technical Overlays**:
  - Anchored Daily **VWAP** (Volume-Weighted Average Price) with dynamic ±2σ Statistical Volatility Bands.
  - Dual EMA (9 & 21) trend momentum filters.
  - 20-Period Volume Moving Average and real-time constituent volume accumulation.
- **Dynamic Support & Resistance Engine**:
  - Automatically maps 1-month and 2-month confluence support and resistance levels.
  - Displays touch bounce counts, price clusters, and institutional rejection zones.

### 2. 📐 Interactive Drawing Suite & Risk:Reward Position Calculator
- **Full Drawing Toolkit**: Trendlines, horizontal support/resistance rays, rectangles, price markers, and measurement tools.
- **Interactive Risk:Reward (R:R) Tool**:
  - Place **Long Position** or **Short Position** tools directly on any candle.
  - Automatically calculates entry price, target (+6%), stop loss (-3%), and real-time R:R ratio.
  - **Persistent User Storage**: All custom drawings and R:R measurements are saved to your account in the cloud.

### 3. 🤖 Multi-Agent AI Strategy Copilot (Gemini + RAG)
- **Chain-of-Thought Institutional Synthesis**:
  - **Alpha Scout**: Hunts for high-probability edges, VWAP bounces, and momentum breakouts.
  - **Devil's Advocate**: Identifies potential bull/bear traps, option chain resistance walls, and volume exhaustion.
  - **Master Synthesizer**: Delivers a definitive verdict with Entry, Target, Stop-Loss, and R:R sizing.
- **Real-Time Market Feeds Attached to RAG**:
  - **RVOL (Relative Volume Z-Score)**: Institutional activity detection.
  - **Market Regime**: ADX trend strength and ATR dynamic stop sizing ($SL = 1.2 \times ATR$).
  - **Option Chain Shifts**: Live Call and Put open interest accumulation tracking.
- **Multi-Turn Conversation Memory**: Retains session context so you can ask natural follow-ups (e.g., *"Should I exit now?"*).

### 4. 🔔 24/7 Real-Time Telegram Alerts
Receive instant, automated notifications directly on Telegram for strictly 3 critical market events:
1. **Main Systematic Strategy Signals**: Confirmed BUY / SELL signals with execution price, target, stop loss, Z-score, and Linreg slope.
2. **S&R Breakout & Reversal Signals**: High-momentum breaks of strong multi-month levels (gap $\ge$ 50 pts) and liquidity sweep reversals.
3. **3:30 PM Mandatory Force Exit**: End-of-day alert confirming all intraday positions are squared off at market close.

### 5. 👤 Personalized User Accounts & Privacy
- **Isolated User Workspaces**: Secure account registration with encrypted credentials.
- **Cloud State Synchronization**: Indicator preferences, drawing tools, and Copilot conversations are preserved across all your devices (desktop, laptop, and mobile).

---

## 📖 How to Use the Terminal

### Step 1: Access the Website & Sign Up
1. Open the terminal at [**https://yourtradebot.duckdns.org**](https://yourtradebot.duckdns.org).
2. Click **Register** to create your trader account.
3. Select your preferred **Trading Style** (Intraday Scalper, Day Trader, Swing Trader, or Options Buyer) to customize how the AI Copilot responds to your questions.

### Step 2: Navigate the Chart & Timeframes
- Use the top navigation bar to switch between **5m**, **15m**, **1h**, and **1d** candle timeframes.
- Use your mouse wheel or trackpad pinch to zoom in/out, and drag horizontally to pan across past market sessions.
- Click the **Indicators** button to toggle VWAP, Volatility Bands, SMA, or Volume overlays.

### Step 3: Draw on the Chart & Calculate Risk:Reward
1. Click the **Tools** icon on the left toolbar.
2. Select **Long Position** or **Short Position**.
3. Click on the chart where you entered a trade.
4. Drag the green Target handle and red Stop-Loss handle to adjust your levels. The tool displays your exact **Risk-to-Reward ratio** in real-time.
5. All drawings save automatically to your account.

### Step 4: Interact with the AI Strategy Copilot
1. Click the **Copilot** panel on the right side of the screen.
2. Type any market question, such as:
   - *"Is NIFTY Call good at 23,050?"*
   - *"Analyze current VWAP slope and volume momentum."*
   - *"What are the key resistance walls from the option chain?"*
3. The AI analyzes real-time candle data, multi-timeframe confluence, and institutional levels to give you a structured recommendation.

### Step 5: Receive Live Telegram Alerts
- Ensure your Telegram bot and chat ID are linked in your settings to get real-time audio and push alerts for verified strategy setups and 3:30 PM session close.

---

## ⚖️ Regulatory Disclaimer

*This software is designed solely for technical charting, algorithmic analysis, and educational purposes. It does NOT provide financial, legal, or investment advice. Trading in equities, derivatives, and financial markets carries significant financial risk. Users are advised to exercise independent judgment and consult with a certified financial advisor before placing any real trades.*
