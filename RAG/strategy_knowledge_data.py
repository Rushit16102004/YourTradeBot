"""
Comprehensive Trading Strategy Knowledge Base, Operational Playbooks & FAQ Bank.
Permanently seeded into ChromaDB 'strategy_knowledge' collection.
"""
from typing import List, Dict, Any

STRATEGY_KNOWLEDGE_DOCS: List[Dict[str, Any]] = [
    # ---------------------------------------------------------
    # 1. Main Strategy Playbook
    # ---------------------------------------------------------
    {
        "id": "strat_main_overview",
        "title": "Main Strategy Rules",
        "category": "STRATEGY_CORE",
        "tags": "main_strategy, vwap, z_score, sma20, linreg_slope, trend_following",
        "content": (
            "Main Strategy Architecture on NIFTY 50 5-Minute Chart:\n"
            "1. Core Indicators: Session VWAP (Blue), ±2σ Exhaustion Bands (Red +2σ / Green -2σ), "
            "SMA 20 (Orange), Linear Regression Slope (5-bar lookback), and Price Z-Score.\n"
            "2. BUY / LONG Entry Conditions:\n"
            "   - Price crosses and closes strictly above Session VWAP.\n"
            "   - Linear Regression Slope turns positive (Slope > +0.02).\n"
            "   - Price Z-Score exceeds Entry Threshold (Z-Score >= 2.00), confirming bullish momentum.\n"
            "   - Price is above the 20-period SMA.\n"
            "3. SELL / EXIT Conditions:\n"
            "   - Linreg Slope flattens and inverts negative (Slope < -0.01).\n"
            "   - Price crosses below 20-period SMA or VWAP.\n"
            "   - Trend exhaustion signaled near +2σ upper band."
        ),
    },
    {
        "id": "strat_vwap_exhaustion_bands",
        "title": "VWAP ±2σ Exhaustion Bands Mean-Reversion Rules",
        "category": "INDICATORS",
        "tags": "vwap, bands, exhaustion, standard_deviation, mean_reversion",
        "content": (
            "VWAP ±2 Standard Deviation (±2σ) Exhaustion Bands Rules:\n"
            "1. Upper Band (+2σ Red Line): Represents extreme statistical overbought territory. "
            "When NIFTY price touches or spikes through +2σ without strong institutional breakout volume, "
            "buyers become exhausted. Never chase long/call entries here. Look for mean-reversion pullbacks back toward Session VWAP.\n"
            "2. Lower Band (-2σ Green Line): Represents extreme statistical oversold territory. "
            "When price spikes down into -2σ, institutional dip buyers step in. Never chase short/put entries at -2σ. "
            "Look for bounce reversals back toward Session VWAP.\n"
            "3. Band Squeeze: When ±2σ bands contract tightly within 40-50 points, volatility is compressing before an explosive expansion."
        ),
    },

    # ---------------------------------------------------------
    # 2. Support & Resistance (S&R) Breakout Strategy Playbook
    # ---------------------------------------------------------
    {
        "id": "strat_sr_breakout_rules",
        "title": "S&R 2-Candle Breakout & Breakdown Strategy Rules",
        "category": "STRATEGY_SR",
        "tags": "sr_breakout, confirmation, runway_filter, strong_levels, call, put",
        "content": (
            "S&R Breakout & Breakdown Operational Playbook (5-Minute Candles):\n"
            "1. Level Strength Requirement: Only triggers against Major Strong S&R Levels (Touch count strictly > 5x, i.e. 6x+ bounces or Major Flip Zone Rectangles).\n"
            "2. BUY CALL (Bullish Resistance Breakout):\n"
            "   - Candle 1 (Breakout): Closes strictly ABOVE a Strong Resistance level.\n"
            "   - Candle 2 (Confirmation): Must close in the SAME upward direction without falling back below the resistance level (Low >= Resistance - 3.5 pts).\n"
            "   - Runway Gap Filter (Crucial): The distance from the broken resistance to the NEXT resistance above MUST be >= 50 points. "
            "If the next resistance is within < 50 points, the signal is REJECTED to prevent getting trapped in tight overhead supply.\n"
            "3. BUY PUT (Bearish Support Breakdown):\n"
            "   - Candle 1 (Breakdown): Closes strictly BELOW a Strong Support level.\n"
            "   - Candle 2 (Confirmation): Must close in the SAME downward direction without recovering back above support (High <= Support + 3.5 pts).\n"
            "   - Runway Gap Filter (Crucial): The distance from broken support to NEXT support below MUST be >= 50 points."
        ),
    },

    # ---------------------------------------------------------
    # 3. S&R Anti-Fakeout & Liquidity Sweep (Trap Reversals)
    # ---------------------------------------------------------
    {
        "id": "strat_sr_reversal_traps",
        "title": "Institutional Trap & Liquidity Sweep Reversal Strategy",
        "category": "STRATEGY_TRAP",
        "tags": "reversal, bull_trap, bear_trap, liquidity_sweep, rejection_wick",
        "content": (
            "Anti-Fakeout Liquidity Trap Reversals (High Probability Institutional Setups):\n"
            "1. Level Strength Requirement: Only triggers against Major S&R Levels with strictly > 5x touches (6x+ bounces or Major Flip Zone Rectangles).\n"
            "2. Bull Trap Reversal (BUY PUT):\n"
            "   - Market high pierces above a Strong Resistance level (sweeping retail breakout buy stops and inducing FOMO buyers).\n"
            "   - The candle body FAILS to sustain above resistance and closes BACK BELOW the level.\n"
            "   - Rejection Wick: The upper shadow/wick MUST be >= 40% of the entire candle range, showing aggressive institutional selling.\n"
            "   - Target Runway: Distance to the next support below MUST be >= 50 points.\n"
            "2. Bear Trap Reversal (BUY CALL):\n"
            "   - Market low pierces below a Strong Support level (triggering retail panic stop-losses).\n"
            "   - The candle body FAILS to sustain below support and closes BACK ABOVE the level.\n"
            "   - Rejection Wick: The lower shadow/wick MUST be >= 40% of the candle range, proving sharp institutional absorption.\n"
            "   - Target Runway: Distance to the next resistance above MUST be >= 50 points."
        ),
    },

    # ---------------------------------------------------------
    # 4. Multi-Month S&R Confluence Architecture (2M, 4M, 1&2M, 1,2,3M, All 4M)
    # ---------------------------------------------------------
    {
        "id": "strat_sr_confluence_logic",
        "title": "4-Month Multi-Horizon S&R Confluence Architecture & Institutional Order Flow",
        "category": "CONFLUENCE",
        "tags": "confluence, 1m, 2m, 4m, macro, multi_month, order_flow, 1_2m, 1_2_3m, all_month",
        "content": (
            "4-Month Multi-Horizon Support & Resistance Confluence Architecture:\n"
            "1. 1-Month (1M): Rolling 20 trading days (~1,500 5m candles). Tactical swing structure and recent pivots.\n"
            "2. 2-Month (2M): Rolling 45 trading days (~3,375 5m candles). Intermediate institutional barriers and multi-week volume nodes.\n"
            "3. 4-Month (4M): Rolling 86-90 trading days (~6,500+ 5m candles). Macro institutional boundaries, quarterly flip zones, and major liquidity pools.\n"
            "4. Multi-Month Confluence Engine (<= 8.0 Points):\n"
            "   - 1&2 Month Confluence: Overlap between 1M swing pivots and 2M intermediate barriers.\n"
            "   - 1,2,3 Month Confluence: Triple-horizon multi-month confluence.\n"
            "   - All Month (1,2,3,4) Confluence: Supreme confluence where levels align across all 4 months, receiving boosted touch counts, maximum thickness, and supreme priority.\n"
            "5. Why Multi-Month Confluence Matters: Institutional algorithms and FII/DII order books execute primarily around multi-month confluence barriers. "
            "Reversals and breakouts at 4-month and all-month confluence levels produce the highest-probability trading opportunities in NIFTY 50."
        ),
    },

    # ---------------------------------------------------------
    # 5. Multi-Timeframe (MTF) Trend Alignment Matrix
    # ---------------------------------------------------------
    {
        "id": "strat_mtf_alignment",
        "title": "Multi-Timeframe (MTF) Alignment Matrix & Execution Guide",
        "category": "MTF_MATRIX",
        "tags": "mtf, alignment, 5m, 15m, 1h, 1d, confluence",
        "content": (
            "Multi-Timeframe (MTF) Trend Matrix Across 5m, 15m, 1H, and 1D:\n"
            "1. Timeframe Roles:\n"
            "   - 5-Minute (5m): Tactical execution & candle trigger.\n"
            "   - 15-Minute (15m): Short-term intraday trend & opening momentum.\n"
            "   - 1-Hour (1H): Structural market direction.\n"
            "   - 1-Day (1D): Macro bias & institutional market regime.\n"
            "2. Trend Scoring per Timeframe:\n"
            "   - Bullish (+1): Price > VWAP and Price > 20 SMA.\n"
            "   - Bearish (-1): Price < VWAP and Price < 20 SMA.\n"
            "   - Neutral (0): Price between VWAP and 20 SMA.\n"
            "3. Execution Confluence Guidelines:\n"
            "   - Bullish Confluence (>= 3 Bullish): Take CALL breakouts with full position size.\n"
            "   - Bearish Confluence (>= 3 Bearish): Take PUT breakdowns with full position size.\n"
            "   - Mixed / Neutral (e.g., 2B / 0S): Trade with reduced lot size (50%) and take quicker profits at +35-40 pts."
        ),
    },

    # ---------------------------------------------------------
    # 6. Market Regimes & Session Management (ORB & Expiry)
    # ---------------------------------------------------------
    {
        "id": "strat_market_regimes_expiry",
        "title": "Market Regimes, Opening Range Breakout (ORB) & Expiry Rules",
        "category": "MARKET_REGIMES",
        "tags": "market_regimes, expiry, orb, thursday, theta, volatility",
        "content": (
            "Market Regimes, Session Dynamics & Expiry Rules on NIFTY 50:\n"
            "1. 15-Minute Opening Range Breakout (ORB: 09:15 - 09:30 IST):\n"
            "   - High and Low of the first 15 minutes define the initial balance.\n"
            "   - If price breaks out above ORB High with MTF Bullish confirmation, high probability of a trending day.\n"
            "   - If price stays trapped inside the ORB for over 90 minutes, market is in a Choppy / Range-bound regime. Favor mean-reversion around VWAP.\n"
            "2. Weekly Expiry Day (Thursday) Dynamics:\n"
            "   - Aggressive Option Theta Decay: Avoid buying deep Out-Of-The-Money (OTM) strikes. Always trade In-The-Money (ITM) or At-The-Money (ATM) options.\n"
            "   - Afternoon Zero-Hero Volatility: Between 13:30 and 15:15 IST, option gamma spikes. Tighten stop loss to 10 points and never hold losing option contracts.\n"
            "3. Trending vs Choppy Regime Tactics:\n"
            "   - Trending Days: VWAP slope is steep (> 0.04), candles ride outside the 20 SMA. Hold positions toward the full 50-70 pt S&R targets.\n"
            "   - Choppy Days: VWAP is completely flat. Price oscillates between +2σ and -2σ bands. Scalp quick reversals and avoid chasing breakouts."
        ),
    },

    # ---------------------------------------------------------
    # 7. Risk Management, Stop Loss & Capital Protection Policy
    # ---------------------------------------------------------
    {
        "id": "strat_risk_policy_disclaimer",
        "title": "Mandatory Risk Management Policy & Statutory Loss Disclaimer",
        "category": "RISK_POLICY",
        "tags": "risk_management, stop_loss, position_sizing, disclaimer, capital_protection",
        "content": (
            "LEGAL DISCLAIMER & CAPITAL PROTECTION POLICY:\n"
            "1. Statutory Warning: Trading equity derivatives (Options & Futures) on the National Stock Exchange of India (NSE) "
            "carries high financial risk. It is possible to lose 100% of invested capital. Algorithmic signals, VWAP bands, "
            "and historical 1M+2M S&R confluence levels are statistical reference tools and DO NOT GUARANTEE PROFITS.\n"
            "2. Maximum Risk Rule: Never risk more than 1.5% to 2.0% of total trading account equity on any single trade.\n"
            "3. Hard Stop-Loss Placement:\n"
            "   - For Breakout Longs: Stop loss must be placed 3.5 to 5.0 points below the broken resistance level.\n"
            "   - For Breakdown Shorts: Stop loss must be placed 3.5 to 5.0 points above the broken support level.\n"
            "   - For Trap Reversals: Stop loss placed strictly 2.0 points beyond the extreme tip of the rejection wick.\n"
            "4. Invalidation Rule: If a 5-minute candle closes in the opposite direction against your signal, exit immediately without hoping."
        ),
    },

    # ---------------------------------------------------------
    # 8. Trader FAQ & Actionable Scenarios
    # ---------------------------------------------------------
    {
        "id": "faq_why_signal_rejected",
        "title": "FAQ: Why did price break a level but no alert was triggered?",
        "category": "FAQ",
        "tags": "faq, runway_filter, rejection, confirmation",
        "content": (
            "Question: Price broke through a line on my chart, but why didn't the system generate a Breakout Alert?\n"
            "Answer: The terminal enforces 3 strict institutional safety filters before generating an alert:\n"
            "1. Runway Distance Filter: The gap to the NEXT resistance/support must be >= 50 points. If the next barrier is only 30-40 points away, "
            "the signal is rejected because there is insufficient profit runway before price clashes with overhead supply.\n"
            "2. 2-Candle Confirmation: Candle 1 must close outside the level, and Candle 2 must confirm continuation without reversing back.\n"
            "3. Level Strength: The level must have at least 4 historical touches (>=4x) or be a major flip zone. Local 1-2 touch lines are ignored."
        ),
    },
    {
        "id": "faq_trading_mixed_mtf",
        "title": "FAQ: How to trade when MTF Matrix is MIXED / NEUTRAL?",
        "category": "FAQ",
        "tags": "faq, mtf_mixed, neutral, position_size",
        "content": (
            "Question: What should I do when a signal triggers but MTF Ribbon says 'MIXED (2B / 0S) - NEUTRAL'?\n"
            "Answer: When MTF is Mixed, higher timeframes (1H/1D) are not in sync with the lower timeframe (5m). This indicates range consolidation.\n"
            "Action Plan:\n"
            "1. Cut position size by 50% (e.g., trade 1 lot instead of 2 lots).\n"
            "2. Book profits quickly at +30 to +40 points instead of waiting for the full 70-point target.\n"
            "3. Trail stop-loss to breakeven as soon as price moves +20 points in your favor."
        ),
    },
    {
        "id": "faq_golden_rectangles_vs_white_lines",
        "title": "FAQ: What is the difference between Golden Rectangle Zones and Pure White Lines?",
        "category": "FAQ",
        "tags": "faq, rectangles, flip_zones, white_lines, colors",
        "content": (
            "Question: What do the different lines and rectangles mean on the chart?\n"
            "Answer:\n"
            "1. Pure White Dashed Lines: Clean major S&R levels with >= 3 to 5 touches within a tight spread (<= 8.0 pts).\n"
            "2. Golden Rectangle Zones (#ffd700 border): Major Institutional S/R Flip Zones with >= 6 to 14 touches across a wider price spread. "
            "The yellow highlighted boundary indicates where the majority of institutional touches occurred (upper or lower).\n"
            "3. Off-White Lines (#cbd5e1): Short-term tactical Local S&R from the most recent 5-7 days."
        ),
    },
    {
        "id": "strat_drawing_tools_and_angle_measurement",
        "title": "On-Chart User Drawing Tools & Trendline Angle Measurement Rules",
        "category": "DRAWING_TOOLS",
        "tags": "drawings, trendline, angle, ray, arrow, measurement, slope, degree",
        "content": (
            "On-Chart User Drawing Tools & Geometric Angle Interpretation on NIFTY 50 Pro Terminal:\n"
            "1. Angle Measurement Formula: Trendline angle is calculated geometrically between anchor point P1 (time1, price1) and anchor point P2 (time2, price2) using atan2(-dy, dx) * (180 / PI).\n"
            "2. Trendline Angle Interpretation:\n"
            "   - Positive Angle (> 0°): Ascending Support Trendline. Indicates bullish swing support or an upward sloping channel. Angles between 20° and 45° indicate healthy sustainable trend; steep angles > 50° indicate blow-off / parabolic momentum.\n"
            "   - Flat / Near Zero Angle (-5° to +5°): Horizontal Support or Resistance barrier (P1 price ≈ P2 price).\n"
            "   - Negative Angle (< 0°): Descending Resistance Trendline. Indicates bearish overhead supply or a downward sloping trend channel. Steep angles < -45° reflect aggressive institutional selling.\n"
            "3. Live Properties & Badge Display: When a user selects or hovers over any drawn trendline or arrow on the chart, the terminal displays the exact Measured Angle (e.g. 23° or -15°), anchor prices P1 and P2, and price delta in ₹ and %."
        ),
    },
    {
        "id": "strat_developer_and_strategy_provider_contact",
        "title": "Strategy Provider & Lead Developer Contact Details",
        "category": "CONTACT",
        "tags": "developer, creator, provider, strategy_provider, contact, email, connect, author, rushit, bodra",
        "content": (
            "Strategy Provider & System Developer Information:\n"
            "• Lead Quantitative Developer & Strategy Provider: Rushit Bodra\n"
            "• Official Contact Email: rushitbodra@gmail.com\n"
            "• Purpose of Contact: Inquiries regarding algorithmic trading strategy access, custom parameter optimization, institutional collaboration, partnership, API integrations, and quantitative system support.\n"
            "• Response Time: Messages sent to rushitbodra@gmail.com are typically reviewed directly by Rushit Bodra."
        ),
    },

    # ---------------------------------------------------------
    # 15. Time-of-Day Institutional Execution Playbook
    # ---------------------------------------------------------
    {
        "id": "strat_time_of_day_windows",
        "title": "Time-of-Day Trading Windows & Risk Playbook",
        "category": "RISK_MANAGEMENT",
        "tags": "time_of_day, trading_hours, lunch_chop, prime_window, square_off, opening_range, ist",
        "content": (
            "Institutional Time-of-Day Execution Rules on NSE NIFTY 50 (IST):\n"
            "1. 09:15 – 09:25 AM (Opening Chaos Zone - RED): Extreme bid-ask spread and gap adjustments. High probability of whipsaws (75% failure rate on early breakouts). Mandate: Wait for the 09:30 AM candle settlement.\n"
            "2. 09:30 – 11:30 AM (Prime Morning Window - GREEN): Institutional order flow peaks. Cleanest trend follow-through for Session VWAP continuations and verified S&R breakouts (> 5x touches).\n"
            "3. 11:30 AM – 01:15 PM (Lunch Chop Zone - DYNAMIC RISK MODIFIER, NOT A VETO): Time of Day is a Risk Modifier (Weight: 15%), NOT a binary veto! While general liquidity dips, if a breakout occurs with expanding volume (RVOL > 1.5) or strong trend regime (ADX > 25), the AI recognizes institutional buying, approves the trade, and simply advises a tighter trailing Stop-Loss (12–15 pts or 1.2x ATR) and scalp sizing instead of blindly rejecting it. If volume is flat/contracted, wait for pullback to Session VWAP or 01:15 PM.\n"
            "4. 01:15 – 02:45 PM (Afternoon Institutional Trend - GREEN): European markets open (13:00–13:30 IST), bringing fresh volume. Excellent for second-leg trend breakouts toward daily S&R targets.\n"
            "5. 03:00 – 03:30 PM (Square-Off Danger Zone - RED): Brokers execute mandatory MIS auto-square-offs at 15:15-15:20 IST. High risk of erratic institutional liquidation spikes. Mandate: Strictly avoid fresh option buys; protect locked-in daily profits."
        ),
    },
    # ---------------------------------------------------------
    # 16. Live Derivatives & Option Chain Intelligence (PCR & Max OI)
    # ---------------------------------------------------------
    {
        "id": "strat_option_chain_pcr_intelligence",
        "title": "Live Derivatives & Option Chain Intelligence (PCR & Max OI)",
        "category": "DERIVATIVES",
        "tags": "option_chain, pcr, open_interest, max_pain, call_writing, put_writing, short_covering",
        "content": (
            "Live Option Chain & Open Interest (OI) Quantitative Framework:\n"
            "1. The 3-Dimensional PCR Master Framework (Total Put OI / Total Call OI):\n"
            "   A. The Standard Directional Framework (Momentum Buyer View):\n"
            "      - PCR < 0.70 (Strong Bullish Momentum): Direction UP 📈. Call buying heavily dominates; traders chasing upside.\n"
            "      - 0.70 to 0.90 (Mildly Bullish / Healthy Rise): Direction UP / SIDEWAYS ↗️. Standard bullish market environment.\n"
            "      - 0.90 to 1.10 (Neutral Zone): Direction SIDEWAYS / RANGEBOUND ↔️. Perfect balance between buyers and sellers; choppy.\n"
            "      - 1.10 to 1.30 (Bearish Momentum): Direction DOWN 📉. Put buying dominates; portfolio hedging or active shorting.\n"
            "   B. The Reversal Framework (The Contrarian Extremes - Rubber Band):\n"
            "      - PCR < 0.50 (Extreme Greed / Overbought): Expected Reversal DOWN 🔴. Market tops out as upside buyers exhaust.\n"
            "      - PCR > 1.40 (Extreme Fear / Oversold): Expected Reversal UP 🟢. Peak panic; explosive short-covering bounce upwards.\n"
            "   C. The Option Writer's Framework (Smart Money for Nifty / Bank Nifty):\n"
            "      - High PCR (> 1.20 - 1.40) = Bullish Support Floor 🟢 (Institutional Put writing creates a hard floor).\n"
            "      - Low PCR (< 0.70 - 0.50) = Bearish Resistance Ceiling 🔴 (Institutional Call writing caps upside).\n"
            "   D. Summary Cheat Sheet Matrix:\n"
            "      * < 0.50: Hyper-Bullish | Bearish Reversal Risk (Top) | Severe Call Writing (Strong Cap)\n"
            "      * 0.60 - 0.80: Bullish | Maintain Trend | Call Writing Dominates\n"
            "      * 0.90 - 1.10: Neutral | No Reversal | Balanced Market\n"
            "      * 1.10 - 1.30: Bearish | Maintain Trend | Put Writing Dominates\n"
            "      * > 1.40: Hyper-Bearish | Bullish Reversal Risk (Bottom) | Severe Put Writing (Strong Floor)\n"
            "2. Max Call OI Strike (Major Institutional Resistance Ceiling): The strike with highest Call OI represents where big option sellers will defend. Always place Call targets before or at this ceiling.\n"
            "3. Max Put OI Strike (Major Institutional Support Floor): The strike with highest Put OI acts as institutional demand floor.\n"
            "4. OI Dynamics: Price rising + PCR rising = Long Buildup (Strong). Price rising + PCR falling = Short-Covering Rally (Fragile)."
        ),
    },
    # ---------------------------------------------------------
    # 17. India VIX & Volatility Regime Master Framework
    # ---------------------------------------------------------
    {
        "id": "strat_india_vix_regime_framework",
        "title": "India VIX & Volatility Regime Master Framework",
        "category": "MARKET_REGIME",
        "tags": "india_vix, volatility, regime, stop_loss_buffer, target_runway, heavyweights, market_breadth",
        "content": (
            "India VIX Volatility Regime & Position Adaptation Framework:\n"
            "1. Low Volatility Regime (VIX < 12.0):\n"
            "   - Market Character: Narrow daily ranges (40-60 pts), low intraday momentum, fast option premium decay.\n"
            "   - Strategy Rule: Focus on short scalps (15-25 pts target, 12-15 pts SL). Never hold out-of-the-money options through lunch chop.\n"
            "2. Normal Trending Regime (12.0 <= VIX <= 16.5):\n"
            "   - Market Character: Balanced institutional trend environment with clean VWAP expansion and validated S&R breakouts (> 5x touches).\n"
            "   - Strategy Rule: Standard targets (40-75 pts) with 18-25 pt Stop-Loss buffers.\n"
            "3. High Volatility Regime (VIX > 16.5):\n"
            "   - Market Character: Violent swings, wide candle ranges, and deep wicks that easily hit tight stop-losses.\n"
            "   - Strategy Rule: Widen Stop-Loss buffer by 12-18 pts (30-45 pts total SL) to avoid noise stop-outs. Reduce position size by 50% to maintain 1-2% account risk.\n"
            "4. NIFTY 50 Heavyweight Breadth: Always check top 5 heavyweights (HDFCBANK, RELIANCE, ICICIBANK, INFY, TCS). If index breaks resistance but Reliance and HDFC Bank are falling, the breakout has high risk of being a bull trap."
        ),
    },
    # ---------------------------------------------------------
    # 18. Multi-Timeframe Fractal Confluence Matrix
    # ---------------------------------------------------------
    {
        "id": "strat_multi_timeframe_fractal_matrix",
        "title": "Multi-Timeframe Fractal Confluence Matrix (15m + 5m + 1m)",
        "category": "MULTI_TIMEFRAME",
        "tags": "multi_timeframe, 15m, 5m, 1m, 3m, rejection_wick, volume_surge, fractal_confluence",
        "content": (
            "3-Tier Multi-Timeframe Fractal Confluence Architecture:\n"
            "1. Tier 1: Macro Trend (15m / Daily Chart):\n"
            "   - Governs the structural directional bias. Identifies 200 EMA slope and daily high/low range.\n"
            "   - Golden Rule: Never buy Calls if 15m is trading strictly below descending 200 EMA into major daily resistance.\n"
            "2. Tier 2: Session Setup (5m Chart):\n"
            "   - Identifies Session VWAP bias, ±2σ Exhaustion Bands, EMA 9/20 slopes, and validated S&R confluence levels (strictly > 5 touches).\n"
            "   - Requires minimum 50-point runway to next S&R ceiling for new entries.\n"
            "3. Tier 3: Execution Trigger (1m / 3m Micro Chart):\n"
            "   - Pinpoints exact candle entry timing without waiting for 5m close lag.\n"
            "   - Bullish Trigger: Lower rejection wick >= 40% of candle range with Volume Burst >= 1.5x of 20MA (Dip Absorption).\n"
            "   - Bearish Trigger: Upper rejection wick >= 40% of candle range with Volume Burst >= 1.5x of 20MA (Peak Rejection)."
        ),
    },
    # ---------------------------------------------------------
    # 19. Contract Specifications & Lot Sizing Framework
    # ---------------------------------------------------------
    {
        "id": "strat_position_sizing_lot_size",
        "title": "Contract Specifications & Lot Sizing Framework (1 Lot = 65 Quantity)",
        "category": "RISK_MANAGEMENT",
        "tags": "lot_size, quantity, 65_quantity, risk_management, capital_risk, position_sizing",
        "content": (
            "Official Contract Sizing & Capital Risk Rules for NIFTY 50 (NSE):\n"
            "1. Lot Size Specification: 1 Contract Lot = STRICTLY 65 QUANTITY (Units).\n"
            "   - 1 Lot = 65 Qty\n"
            "   - 2 Lots = 130 Qty\n"
            "   - 3 Lots = 195 Qty\n"
            "   - 4 Lots = 260 Qty\n"
            "2. Maximum Capital Risk: Never risk more than 1.0% to 2.0% of trading account capital per trade setup.\n"
            "3. Lot Size Formula: Recommended Lots = floor(Max Risk in INR / (Stop-Loss Points * 65)).\n"
            "   - Example: On ₹100,000 capital risking 1.5% (₹1,500) with a 20-point Stop-Loss: Risk per lot = 20 * 65 = ₹1,300 -> Exactly 1 Lot (65 Quantity).\n"
            "4. Scalper Leverage Cap: Intraday scalpers should never exceed 4 lots to avoid margin overexposure."
        ),
    },
    # ---------------------------------------------------------
    # 20. Tuesday Weekly Expiry Trading Playbook
    # ---------------------------------------------------------
    {
        "id": "strat_tuesday_weekly_expiry",
        "title": "Tuesday Weekly Expiry Intraday Trading Playbook",
        "category": "EXPIRY_STRATEGY",
        "tags": "tuesday_expiry, weekly_expiry, theta_decay, gamma_spikes, zero_to_hero, mis_square_off",
        "content": (
            "Tuesday Weekly Expiry Intraday Trading Dynamics & Rules:\n"
            "1. Expiry Day Identification: Weekly contract expiry takes place every TUESDAY.\n"
            "2. Morning Session (09:15 - 11:30 IST): High Theta decay. Out-of-the-money (OTM) options lose 30-50% value rapidly if underlying stays range-bound. Buy strictly In-The-Money (ITM) or ATM on verified S&R breakouts (>5x touches).\n"
            "3. Lunch Session (11:30 - 13:15 IST): Accelerated premium decay. Avoid long option holds.\n"
            "4. Afternoon Gamma Blast Window (13:15 - 14:45 IST): Peak Gamma sensitivity. At-the-money (ATM) options experience sudden 2x-5x surges on directional momentum. High risk/reward directional scalping.\n"
            "5. Broker Auto-Square-Off Mandate (15:00 - 15:30 IST): Mandatory intraday MIS positions are liquidated between 15:15 and 15:20 IST. Traders must close all intraday option buys by 15:00-15:10 IST to avoid sudden slippage."
        ),
    },
    # ---------------------------------------------------------
    # 21. Complete Chart Drawing Tools Guide & AI Interpretation
    # ---------------------------------------------------------
    {
        "id": "strat_drawing_tools_complete_guide",
        "title": "Complete Chart Drawing Tools Architecture & AI Semantic Interpretation",
        "category": "DRAWING_TOOLS",
        "tags": "drawings, trendline, ray, rectangle, target_sl, channel, fibonacci, support_zone, demand_zone",
        "content": (
            "Complete Chart Drawing Tools Architecture & AI Semantic Interpretation on NIFTY 50 Terminal:\n"
            "1. Trendline (📈 / 📉):\n"
            "   - Purpose: Connects 2 or more ascending swing lows (Bullish dynamic support) or descending swing highs (Bearish dynamic resistance).\n"
            "   - AI Interpretation: Evaluates geometric slope angle (30°-45° is healthy institutional trend; > 60° is unsustainable climax). Detects breakouts when a 5m candle closes outside the trendline with institutional volume.\n"
            "2. Horizontal Ray / Line (📍):\n"
            "   - Purpose: Marks an exact static institutional price level projected into the future (e.g., Previous Day High, Session Open, or major swing pivot).\n"
            "   - AI Interpretation: Audits alignment against live Option Chain OI walls (Max Call/Put OI) and verifies whether the level has > 5 confirmed historical touches.\n"
            "3. Rectangle / Supply-Demand Zone Box (🔲):\n"
            "   - Purpose: Highlights an institutional Order Block, Supply Zone, or Demand Floor (a price corridor rather than a single line).\n"
            "   - AI Interpretation: Recognizes high-volume accumulation/distribution ranges. Proactively warns traders against chasing Longs inside overhead supply or shorting into demand.\n"
            "4. Target & Stop-Loss Box (🎯):\n"
            "   - Purpose: Visualizes active trade execution: Entry Price, Profit Target runway, and Protective Stop-Loss with minimum 1:2.0 Risk-Reward ratio.\n"
            "   - Platform Auto-Tracking: When placed on chart, PredictionEngine automatically logs the setup into the database, monitors live ticks, and calculates realized PnL in points and ₹ strictly at 65 quantity per lot.\n"
            "5. Parallel Channel (🛤️):\n"
            "   - Purpose: Encloses price action between two parallel trendlines to map trending continuation corridors.\n"
            "   - AI Interpretation: Uses the channel midline as an equilibrium pivot and the upper/lower boundary lines for mean-reversion scalping.\n"
            "6. Fibonacci Retracement (📐):\n"
            "   - Purpose: Measures percentage pullbacks (38.2%, 50.0%, 61.8% Golden Ratio) following an institutional impulse expansion.\n"
            "   - AI Interpretation: Validates high-conviction continuation entries when the 50.0% or 61.8% golden pocket converges with Session VWAP or verified S&R levels."
        ),
    },
    # ---------------------------------------------------------
    # 22. Institutional Trading Dictionary & Technical Words Glossary
    # ---------------------------------------------------------
    {
        "id": "strat_technical_glossary_dictionary",
        "title": "Institutional Trading Dictionary & Technical Words Glossary",
        "category": "GLOSSARY",
        "tags": "glossary, dictionary, oi, open_interest, pcr, support, resistance, vix, vwap, ema, rsi, macd, atr, supertrend, tuesday_expiry, 65_quantity, lunch_chop",
        "content": (
            "Institutional Trading Dictionary & Technical Words Glossary for NIFTY 50 Terminal:\n"
            "1. OI (Open Interest) & 'IO':\n"
            "   - Definition: The total number of open, unsettled derivative option contracts currently held by market participants.\n"
            "   - Max Call OI (Ceiling / Resistance): Strike with the largest Call open interest. Smart money writes calls here, creating a strong ceiling.\n"
            "   - Max Put OI (Floor / Support): Strike with the largest Put open interest. Smart money writes puts here, creating a strong floor.\n"
            "2. PCR (Put-Call Ratio):\n"
            "   - Formula: PCR = Total Put Open Interest / Total Call Open Interest.\n"
            "   - Interpretation: 3-Part Framework: (1) Standard: <0.70 Strong Bullish, 0.70-0.90 Mild Bullish, 0.90-1.10 Neutral, 1.10-1.30 Bearish; (2) Contrarian Reversal: <0.50 Overbought Bearish Top Risk, >1.40 Oversold Bullish Bottom Bounce Risk; (3) Smart Money Writers: High PCR (>1.20) Put Writing Floor Support, Low PCR (<0.70) Call Writing Ceiling Resistance.\n"
            "3. Support & Resistance (S&R):\n"
            "   - Support: A price floor where institutional buying interest absorbs selling pressure.\n"
            "   - Resistance: A price ceiling where institutional profit-taking and shorting overpower buyers.\n"
            "   - Strict Platform Rule: A level is institutionally validated ONLY if it has > 5 confirmed touches. Levels with < 5 touches are weak and prone to retail sweeps.\n"
            "4. India VIX (Volatility Index):\n"
            "   - Real Market Value: ~17.16 – 17.20 (measures expected 30-day market volatility).\n"
            "   - Application: 15–19 VIX indicates normal trend days with standard 20 pt Stop-Loss (₹1,300 per lot on 65 qty) and 40–60 pt target runways.\n"
            "5. Session VWAP & ±2σ Standard Deviation Bands:\n"
            "   - Session VWAP: The volume-weighted average benchmark price paid by institutional players since 09:15 AM.\n"
            "   - ±1σ Corridor: Primary institutional accumulation zone. Trading above +1σ confirms trend strength.\n"
            "   - ±2σ Exhaustion: Extreme statistical stretch. Buying at +2σ or selling at -2σ carries high mean-reversion counter-wave risk.\n"
            "6. Technical Indicators (EMA, RSI, MACD, ATR, Supertrend):\n"
            "   - EMA (9, 20, 50, 200): Trend filters. Price above EMA 20 with positive slope confirms bullish tailwind.\n"
            "   - RSI (14): Relative Strength Index (0–100). > 70 is overbought; < 30 is oversold.\n"
            "   - MACD (12, 26, 9): Trend momentum indicator. Histogram expansion signals acceleration.\n"
            "   - ATR (14): Average True Range per 5m candle. Used to place stop loss buffers outside normal market noise.\n"
            "   - Supertrend (10, 3.0): Volatility trailing stop used for managing multi-lot runner contracts.\n"
            "7. Intraday Trading Dynamics (Tuesday Expiry, 65 Qty, Lunch Chop):\n"
            "   - Tuesday Weekly Expiry: Official weekly expiry day. Rapid theta decay post-12:00 PM; explosive gamma moves post-13:15 IST.\n"
            "   - Contract Lot Sizing: STRICTLY 1 Lot = 65 Quantity on NIFTY (1 Lot = 65, 2 Lots = 130, 3 Lots = 195).\n"
            "   - Lunch Chop (11:30–13:15 IST): European pre-market lull. Volume contracts and false breakout rate exceeds 65%."
        ),
    },
    {
        "id": "strat_ai_mentor_risk_manager_rules",
        "title": "Senior Prop Trader & Risk Manager Mandate: Critical Trade Evaluation (No Yes-Man Rule)",
        "category": "risk_management",
        "tags": "risk_manager, prop_desk, trade_evaluation, call_or_put, can_i_enter, should_i_buy, trap_avoidance",
        "content": (
            "Institutional Prop Desk Risk Manager Mandate — Critical Trade Direction Evaluation:\n"
            "1. THE 'NO YES-MAN' PRINCIPLE:\n"
            "   - When a trader asks 'Can I buy PUT?', 'Can I buy CALL?', 'Should I buy/sell?', or 'Can I enter now?', the AI MUST NEVER blindly manufacture a setup in that direction to please the user.\n"
            "   - The AI's highest fiduciary responsibility is CAPITAL PRESERVATION: saying NO to a bad trade is 10x more valuable than endorsing an impulsive setup.\n"
            "2. OBJECTIVE DIRECTIONAL EVALUATION PROTOCOL:\n"
            "   - Call Inquiry ('Can I buy Call?'):\n"
            "     * If Price is +2σ / +3σ overextended above Session VWAP -> REJECT: '❌ NO, DO NOT BUY CALLS HERE. Price is in an extreme exhaustion trap (+2σ/+3σ) where institutional buyers take profits. Buying here offers negative risk-reward.'\n"
            "     * If Price is within 40 pts of Max Call OI Resistance -> REJECT: '❌ NO, DO NOT BUY CALLS HERE. You are buying directly into the institutional Call OI ceiling.'\n"
            "     * If Price is below Session VWAP -> REJECT: '❌ NO, DO NOT BUY CALLS HERE. Price is below VWAP, fighting the intraday downtrend.'\n"
            "     * If Price is in a clean pullback retesting Session VWAP or EMA 20 with bullish wick -> APPROVE: '✅ YES, A CALL RETEST SETUP IS VALID AT THIS LEVEL. Enter with SL strictly below VWAP.'\n"
            "   - Put Inquiry ('Can I buy Put?'):\n"
            "     * If Price is holding above Session VWAP with bullish EMA stack and PCR > 1.05 -> REJECT: '❌ NO, DO NOT BUY PUTS RIGHT NOW. Price is in a strong uptrend above Session VWAP, and Put writers are actively defending support. Shorting here is counter-trend suicide.'\n"
            "     * If Price is at -2σ oversold floor -> REJECT: '❌ NO, DO NOT BUY PUTS HERE. Price is at the -2σ oversold floor; sellers are exhausted and risk of an institutional short squeeze is high.'\n"
            "     * If Price decisively breaks below Session VWAP on high volume -> APPROVE: '✅ YES, A PUT SETUP IS TECHNICALLY FAVORED. Short on VWAP relief retest with tight SL above VWAP.'\n"
            "   - General Entry Inquiry ('Can I enter now?' / 'Good time to enter?'):\n"
            "     * If time is in Lunch Window (11:30–13:15 IST) -> TIME IS A RISK MODIFIER (15% WEIGHT), NOT A VETO: Check RVOL and Market Regime. If breakout shows expanding volume (RVOL > 1.5) or strong trend (ADX > 25), smart money is active: APPROVE SETUP with tight trailing SL (12–15 pts or 1.2x ATR) and 1 Lot (65 qty) scalp sizing. If volume is flat or contracting (RVOL < 1.0), advise patience: '⚠️ AWAIT VWAP RETEST / 13:15 IST. Volume is subdued in lunch window; wait for a pullback to Session VWAP or European open.' Never blindly veto on time alone.\n"
            "     * If no clear S&R (> 5 touches) or VWAP setup is formed -> ADVISE PATIENCE: '⚠️ DO NOT ENTER YET. Price is in no-man\'s land between S&R levels. Wait for a high-probability boundary.'\n"
            "3. HUMAN MENTORSHIP COMMUNICATION TONE:\n"
            "   - Speak honestly, directly, and constructively like a senior prop trader sitting right next to the trader.\n"
            "   - State the verdict clearly at the very top (e.g., '❌ NOT RECOMMENDED', '⚠️ DO NOT ENTER YET', '✅ VALID SETUP').\n"
            "   - Explain the exact institutional reason (VWAP deviation, Call/Put OI walls, Lunch Chop, S&R touches).\n"
            "   - Provide the specific conditions the trader MUST wait for before taking action."
        ),
    },
    {
        "id": "strat_complete_indicator_playbook_and_calculations",
        "title": "Complete Institutional Indicator Playbook: Mathematical Formulas, Parameters, and CALL/PUT/NEUTRAL Condition Rules",
        "category": "indicators",
        "tags": "indicators, vwap, ema, supertrend, rsi, macd, cpr, bollinger_bands, adx, atr, parabolic_sar, volume, call_or_put_rules",
        "content": (
            "Complete Institutional Indicator Playbook — Quantitative Formulas, Parameters & Signal Rules:\n"
            "1. Session VWAP (Volume-Weighted Average Price) & ±2σ Bands:\n"
            "   - Mathematical Formula: VWAP = ∑(Typical_Price * Volume) / ∑(Volume), where Typical_Price = (High + Low + Close) / 3. Standard deviation σ = sqrt(∑(Volume * (TP - VWAP)²) / ∑(Volume)).\n"
            "   - Parameters: Resets daily at 09:15 AM IST. Bands at ±1.0σ and ±2.0σ.\n"
            "   - Signal Rules:\n"
            "     * CALL: Price trading above Session VWAP with upward slope (> 0.0) -> Institutional accumulation.\n"
            "     * PUT: Price trading below Session VWAP with downward slope (< 0.0) -> Institutional distribution.\n"
            "     * OVERBOUGHT REVERSAL WATCH: Price piercing Upper +2σ Band -> Bull exhaustion trap, high risk of mean-reversion drop.\n"
            "     * OVERSOLD REVERSAL WATCH: Price piercing Lower -2σ Band -> Bear trap, high risk of short squeeze.\n\n"
            "2. Multi-Period Exponential Moving Averages (EMA 9, 20, 50, 200):\n"
            "   - Formula: EMA(t) = Close(t) * (2 / (N + 1)) + EMA(t-1) * (1 - (2 / (N + 1))).\n"
            "   - Signal Rules:\n"
            "     * CALL: EMA 9 > EMA 20 > EMA 50 with Price >= EMA 20 (Bullish Stack).\n"
            "     * PUT: EMA 9 < EMA 20 < EMA 50 with Price < EMA 20 (Bearish Stack).\n"
            "     * NEUTRAL: Moving averages crossing, flattening, or price oscillating between EMA 20 and EMA 50.\n\n"
            "3. Supertrend (10, 3.0 ATR):\n"
            "   - Formula: Basic Upper Band = (High + Low) / 2 + (Multiplier * ATR(Period)). Basic Lower Band = (High + Low) / 2 - (Multiplier * ATR(Period)).\n"
            "   - Signal Rules:\n"
            "     * CALL: Price closes above previous Supertrend Upper Band -> Green trailing support.\n"
            "     * PUT: Price closes below previous Supertrend Lower Band -> Red trailing resistance.\n\n"
            "4. Relative Strength Index (RSI 14):\n"
            "   - Formula: RSI = 100 - (100 / (1 + RS)), where RS = Average_Gain / Average_Loss over 14 bars.\n"
            "   - Signal Rules:\n"
            "     * CALL: RSI between 55 and 70 (Bullish momentum expansion), or RSI <= 30 with bullish wick rejection (oversold reversal).\n"
            "     * PUT: RSI between 30 and 45 (Bearish momentum expansion), or RSI >= 70 with bearish wick rejection (overbought reversal).\n"
            "     * NEUTRAL: RSI between 45 and 55 (Rangebound chop).\n\n"
            "5. Moving Average Convergence Divergence (MACD 12, 26, 9):\n"
            "   - Formula: MACD_Line = EMA(Close, 12) - EMA(Close, 26). Signal_Line = EMA(MACD_Line, 9). Histogram = MACD_Line - Signal_Line.\n"
            "   - Signal Rules:\n"
            "     * CALL: Histogram > 0 and expanding, with MACD Line > Signal Line.\n"
            "     * PUT: Histogram < 0 and expanding, with MACD Line < Signal Line.\n"
            "     * NEUTRAL: Histogram contracting near zero line.\n\n"
            "6. Central Pivot Range (CPR & Floor Pivots):\n"
            "   - Formula: Pivot (P) = (Prior_High + Prior_Low + Prior_Close) / 3. Bottom Central (BC) = (Prior_High + Prior_Low) / 2. Top Central (TC) = (P - BC) + P.\n"
            "   - Signal Rules:\n"
            "     * CALL: Price trading above TC floor -> Bullish day bias.\n"
            "     * PUT: Price trading below BC ceiling -> Bearish day bias.\n"
            "     * NEUTRAL: Price trading inside CPR (between BC and TC) -> High-chop consolidation zone.\n"
            "     * CPR Width: Narrow CPR (< 35 pts) indicates trending breakout day; Wide CPR (> 50 pts) indicates sideways rangebound day.\n\n"
            "7. Average Directional Index (ADX 14, +DI, -DI):\n"
            "   - Formula: Directional movement (+DM, -DM) smoothed by 14-period Wilder MA divided by ATR(14). ADX = 14-period SMA of DX.\n"
            "   - Signal Rules:\n"
            "     * CALL: ADX >= 20 with +DI > -DI -> Strong directional uptrend.\n"
            "     * PUT: ADX >= 20 with -DI > +DI -> Strong directional downtrend.\n"
            "     * NEUTRAL: ADX < 20 -> Absence of trend, low momentum.\n\n"
            "8. Parabolic SAR (0.02, 0.2):\n"
            "   - Formula: SAR(t+1) = SAR(t) + AF * (EP - SAR(t)), Acceleration Factor starting at 0.02, incrementing 0.02 to max 0.20.\n"
            "   - Signal Rules:\n"
            "     * CALL: Dots below price candles -> Bullish trailing stop.\n"
            "     * PUT: Dots above price candles -> Bearish trailing stop.\n\n"
            "9. Volume Dynamics (Top-50 Constituent Sum + 20 MA):\n"
            "   - Formula: Exact sum of all 50 official NIFTY 50 constituent volumes per 5m candle bucket.\n"
            "   - Signal Rules:\n"
            "     * CALL: Volume >= 1.2x 20MA on green candles -> Institutional accumulation.\n"
            "     * PUT: Volume >= 1.2x 20MA on red candles -> Institutional distribution.\n"
            "     * NEUTRAL: Volume < 0.8x 20MA -> Retail low-conviction consolidation.\n\n"
            "10. INSTITUTIONAL 3-LAYER CONFLUENCE MANDATE:\n"
            "    - An elite trader NEVER trades on a single indicator in isolation.\n"
            "    - High-probability trades require confluence of: (1) Structure (Session VWAP or CPR), (2) Momentum (RSI/MACD), and (3) Institutional Wall (PCR / S&R > 5x touches)."
        ),
    },

    # ---------------------------------------------------------
    # 24. Classical Chart Patterns Master Playbook
    # ---------------------------------------------------------
    {
        "id": "strat_classical_chart_patterns_playbook",
        "title": "Classical Chart Patterns Master Playbook (Head & Shoulders, Triangles, Wedges, Flags, Double Tops)",
        "category": "PATTERNS",
        "tags": "patterns, head_and_shoulders, inverse_head_and_shoulders, triangles, ascending_triangle, descending_triangle, symmetrical_triangle, double_top, double_bottom, wedges, flags, pennants",
        "content": (
            "Classical Chart Pattern Quantitative Playbook for NIFTY 50 (5m / 15m / 1h Timeframes):\n\n"
            "1. Head and Shoulders (Bearish Reversal) & Inverse Head and Shoulders (Bullish Reversal):\n"
            "   - Structure: Consists of 3 consecutive peaks/troughs: Left Shoulder, Head (highest/lowest extrema), and Right Shoulder (balanced within 1.5% of Left Shoulder).\n"
            "   - Neckline: Dynamic or horizontal baseline connecting the two reaction valleys (or peaks in Inverse H&S).\n"
            "   - Breakout Confirmation Rule: Strictly requires a 2-candle close beyond the neckline, or a relief retest with a rejection wick.\n"
            "   - Target Calculation: Target = Neckline minus (Head minus Neckline) projected downward for Bearish H&S; Neckline plus depth projected upward for Inverse H&S.\n"
            "   - Stop Loss: Placed strictly beyond the Right Shoulder apex (e.g., RS + 5-10 pts).\n"
            "   - Institutional Volume Clue: Diminishing volume on the Head and Right Shoulder, followed by an aggressive expansion volume surge (> 1.2x 20MA) upon Neckline breakdown.\n\n"
            "2. Triangle Patterns (Ascending, Descending, Symmetrical):\n"
            "   - Ascending Triangle (Bullish Accumulation): Flat horizontal resistance ceiling paired with ascending higher swing lows. Buyers absorb selling pressure at higher levels. Breakout target = Base height added to ceiling.\n"
            "   - Descending Triangle (Bearish Distribution): Flat horizontal support floor paired with descending lower swing highs. Sellers press lower. Breakdown target = Base height subtracted from floor.\n"
            "   - Symmetrical Triangle (Volatility Coil): Lower highs converging with higher lows into an apex. Volatility compresses dramatically before a directional expansion burst (measured by base width).\n\n"
            "3. Double Top ('M' Pattern) & Double Bottom ('W' Pattern):\n"
            "   - Double Top: Two major price peaks tested at the same price zone (+/- 0.35% tolerance). Breakdown below the intervening valley (Neckline) confirms institutional distribution. Target = Peak height projected down from Neckline.\n"
            "   - Double Bottom: Two major price troughs tested at the same support zone (+/- 0.35% tolerance). Breakout above intervening peak (Neckline) confirms institutional accumulation. Target = Valley depth projected up from Neckline.\n\n"
            "4. Flags & Pennants (High-Momentum Continuation):\n"
            "   - Bull Flag: Vertical impulsive pole followed by a tight downward-sloping rectangular channel. Breakout above channel upper boundary triggers rapid continuation (Target = Flag pole length).\n"
            "   - Bear Flag: Sharp impulsive drop followed by a shallow upward-sloping consolidation. Breakdown triggers swift continuation.\n\n"
            "5. Wedges (Exhaustion Reversals):\n"
            "   - Rising Wedge: Upward sloping boundaries with support rising steeper than resistance. Signals momentum exhaustion and an impending bearish breakdown.\n"
            "   - Falling Wedge: Downward sloping boundaries with resistance dropping steeper than support. Signals seller exhaustion and an impending bullish breakout."
        ),
    },

    # ---------------------------------------------------------
    # 25. Harmonic Patterns & Fibonacci Potential Reversal Zones (PRZ)
    # ---------------------------------------------------------
    {
        "id": "strat_harmonic_patterns_and_fibonacci_playbook",
        "title": "Harmonic Patterns & Fibonacci Potential Reversal Zones (Butterfly, Gartley, Bat, Crab)",
        "category": "HARMONICS",
        "tags": "harmonic, butterfly, gartley, bat, crab, fibonacci, prz, reversal, xabcd, 0.786, 1.272, 1.618",
        "content": (
            "Harmonic Patterns & Fibonacci XABCD Quantitative Framework for NIFTY 50:\n\n"
            "1. Harmonic Trading Foundations:\n"
            "   - Harmonic patterns are geometric price structures defined by precise Fibonacci ratios (0.382, 0.500, 0.618, 0.786, 0.886, 1.272, 1.618).\n"
            "   - Point D represents the Potential Reversal Zone (PRZ), where smart money institutional algorithms execute high-conviction counter-trend entries.\n\n"
            "2. BUTTERFLY PATTERN (The King of Extension Reversals):\n"
            "   - Originating Leg: X to A.\n"
            "   - Point B: Strict 0.786 Fibonacci retracement of XA (the defining signature of a valid Butterfly).\n"
            "   - Point C: Retraces between 0.382 and 0.886 of leg AB.\n"
            "   - Point D (PRZ Trigger): Extended Fibonacci projection past X:\n"
            "     * D is strictly a 1.272 to 1.618 Fibonacci extension of the primary XA leg!\n"
            "     * CD leg is simultaneously an extreme 1.618 to 2.618 projection of BC.\n"
            "   - Execution Rules at Point D:\n"
            "     * Bullish Butterfly: Buy at D in the PRZ floor. Target 1 = 0.382 of CD; Target 2 = 0.618 of CD. Stop Loss placed strictly beyond 1.618 XA.\n"
            "     * Bearish Butterfly: Sell at D in the PRZ ceiling. Target 1 = 0.382 of CD; Target 2 = 0.618 of CD. Stop Loss placed strictly above 1.618 XA.\n\n"
            "3. GARTLEY PATTERN (The Classical Retracement Harmonic):\n"
            "   - B point at strict 0.618 retracement of XA.\n"
            "   - D point at exact 0.786 retracement of XA.\n"
            "   - Reversal trigger at D with Target 1 at 0.382 AD, Target 2 at 0.618 AD, SL placed beyond X.\n\n"
            "4. BAT PATTERN (The Deep Reversal Harmonic):\n"
            "   - B point is shallow (0.382 to 0.500 of XA).\n"
            "   - D point is an exact, deep 0.886 Fibonacci retracement of XA.\n"
            "   - High-probability PRZ bounce with very tight Stop Loss just beyond point X.\n\n"
            "5. CRAB PATTERN (The Extreme Volatility Harmonic):\n"
            "   - B point at 0.382 to 0.618 of XA.\n"
            "   - D point extends to an extreme 1.618 Fibonacci extension of XA with 2.618 - 3.618 BC projection."
        ),
    },

    # ---------------------------------------------------------
    # 26. Candlestick Formations & Price Action Reversals
    # ---------------------------------------------------------
    {
        "id": "strat_candlestick_reversal_patterns_playbook",
        "title": "Candlestick Formations & Price Action Reversals (Pin Bar, Engulfing, Morning Star, Doji)",
        "category": "CANDLESTICK_PATTERNS",
        "tags": "candlestick, pin_bar, hammer, shooting_star, engulfing, morning_star, evening_star, doji, rejection_wicks",
        "content": (
            "Institutional Candlestick Reversal & Wick Rejection Framework for NIFTY 50:\n\n"
            "1. Pin Bar (Hammer & Shooting Star):\n"
            "   - Geometry: Body is small (<= 30% of total bar range); long rejection wick is >= 60-70% of total range.\n"
            "   - Bullish Pin Bar (Hammer): Lower wick rejection at Session VWAP, CPR TC, or S&R Support (> 5x touches) confirms institutional dip absorption. Enter above high of pin bar.\n"
            "   - Bearish Pin Bar (Shooting Star): Upper wick rejection at +2σ Band, CPR BC, or S&R Resistance (> 5x touches) confirms overhead institutional distribution. Enter below low of shooting star.\n\n"
            "2. Bullish & Bearish Engulfing:\n"
            "   - Bullish Engulfing: Current candle's green body completely engulfs prior red candle's body with volume surge >= 1.2x 20MA. Confirms immediate buyer takeover.\n"
            "   - Bearish Engulfing: Current candle's red body completely engulfs prior green candle's body with volume expansion. Confirms seller dominance.\n\n"
            "3. Morning Star & Evening Star (3-Candle Reversal Sequences):\n"
            "   - Morning Star (Bullish Reversal): (1) Strong red candle, (2) Small-bodied star/doji gapping down, (3) Strong green candle closing > 50% into candle 1.\n"
            "   - Evening Star (Bearish Reversal): (1) Strong green candle, (2) Small-bodied star/doji gapping up, (3) Strong red candle closing > 50% into candle 1.\n\n"
            "4. Doji (Equilibrium & Compression):\n"
            "   - Open and close are almost identical (body <= 10% of candle range). Represents balance between buyers and sellers; wait for next candle breakout."
        ),
    },
    # ---------------------------------------------------------
    # 27. Personal Brain & Pro-Trader Confluence Philosophy
    # ---------------------------------------------------------
    {
        "id": "strat_personal_brain_philosophy",
        "title": "Personal Trading Brain & Multi-Factor Confluence Philosophy (Beyond Rigid Rule-Based Trading)",
        "category": "PERSONAL_BRAIN",
        "tags": "personal_brain, confluence, pro_trader, intuition, probability, flexible_thinking, trade_suggestions",
        "content": (
            "Senior Quantitative Pro-Trader Personal Brain Philosophy:\n\n"
            "1. NO RIGID SINGLE-INDICATOR VETOES:\n"
            "   - Market reality is multi-dimensional. A single lagging indicator or a slightly overbought oscillator does NOT invalidate a high-probability trade.\n"
            "   - Different indicators measure different aspects: VWAP measures volume-weighted value, EMAs measure trend inertia, Oscillators measure speed, S&R measures order-book liquidity, and Option Chain measures institutional open interest.\n"
            "   - Pro traders never say 'Indicator X is opposing, so this entry is bad'. Instead, they weigh the overall confluence (e.g. 75% bullish balance) and assess the friction.\n\n"
            "2. THE PROBABILISTIC BRAIN MINDSET:\n"
            "   - Trading is an asymmetric risk game. When strong volume expansion, positive market breadth, and S&R breakouts converge, a trade has an 80%+ win expectancy even if RSI is 68 (overbought) or time is approaching lunch.\n"
            "   - Rather than blocking the trade with an outright 'NO', the Personal Brain provides adaptive execution options:\n"
            "     * Option A (Aggressive Momentum Scalp): 1 Lot (65 qty), tight 12-15 pt stop-loss, quick target.\n"
            "     * Option B (Patient High-Conviction Pullback): Wait for 5m candle retest of VWAP or broken S&R before entering.\n\n"
            "3. CONTINUOUS ADAPTIVE COACHING:\n"
            "   - Always guide the trader on HOW to trade the opportunity safely with disciplined risk parameters (strictly 1 Lot = 65 Qty), rather than being a rigid roadblock."
        ),
    },

    # ---------------------------------------------------------
    # 28. Personal Brain: Resolving Indicator Conflicts in Live Markets
    # ---------------------------------------------------------
    {
        "id": "strat_personal_brain_indicator_conflicts",
        "title": "Personal Brain: How to Resolve Conflicting Indicators in Real-Time",
        "category": "PERSONAL_BRAIN",
        "tags": "indicator_conflict, vwap_vs_rsi, ema_vs_lunch, volume_vs_sr, resolution, pro_playbook",
        "content": (
            "Pro-Trader Playbook for Resolving Indicator Conflicts:\n\n"
            "1. Conflict 1: Price is Above Session VWAP (+1σ to +2σ) but RSI is Overbought (> 70):\n"
            "   - Resolution: In strong institutional momentum trends, RSI stays overbought for extended rallies. Never short or blindly reject Calls at RSI 70.\n"
            "   - Brain Suggestion: Valid Call scalp. Enter with 1 Lot (65 qty), place tight SL below the breakout candle low, and book 50% gains at +25 pts.\n\n"
            "2. Conflict 2: Price is Breaking Out of Resistance but Broken Level has only 3-4 Touches (< 5):\n"
            "   - Resolution: While 5+ touches provide maximum barrier strength, 3-4 touch levels still represent active supply zones.\n"
            "   - Brain Suggestion: Treat as an Adaptive Breakout Scalp. Wait for 5m candle close confirmation; use a 15-pt trailing SL.\n\n"
            "3. Conflict 3: Trend is Bullish but Time is in Lunch Chop (11:30–13:15 IST):\n"
            "   - Resolution: Lunch chop has muted volume, but trending days still provide continuation moves.\n"
            "   - Brain Suggestion: Do not take market breakout orders. Instead, place limit buy orders near Session VWAP or EMA 20 support to capture discount pullbacks with minimal risk.\n\n"
            "4. Conflict 4: Price is Below VWAP but Forming Bullish Absorption at Major S&R Support:\n"
            "   - Resolution: This is a high-reward VWAP Reclaim Long Setup. Enter Call on lower rejection wick with SL below the day's swing low; target is Session VWAP (+30 to +50 pts)."
        ),
    },

    # ---------------------------------------------------------
    # 29. Personal Brain: 4 Core Discretionary Setup Modes
    # ---------------------------------------------------------
    {
        "id": "strat_personal_brain_setup_modes",
        "title": "Personal Brain: 4 Core Discretionary Setup Modes (Momentum Scalp, Pullback Retest, Trap Fade, Breakout)",
        "category": "PERSONAL_BRAIN",
        "tags": "setup_modes, momentum_scalp, pullback_retest, trap_fade, breakout, trade_types",
        "content": (
            "The 4 Core Discretionary Trade Setups of the Personal Brain:\n\n"
            "1. High-Conviction Trend Continuation (Confluence >= 75%):\n"
            "   - Trigger: Price above VWAP, EMAs bullish (9 > 20 > 50), PCR > 1.05, clear runway to Max Call OI.\n"
            "   - Execution: 1–2 Lots (65–130 qty), standard 20 pt Stop-Loss (₹1,300/lot), target 40–60 pts.\n\n"
            "2. Adaptive Momentum Scalp (Confluence 55% - 74%):\n"
            "   - Trigger: Strong 5m breakout candle with volume expansion (> 1.2x 20MA), even if 1 indicator (e.g. RSI or time window) suggests caution.\n"
            "   - Execution: Strictly 1 Lot (65 qty), tight 12–15 pt Stop-Loss (₹780–₹975 risk), target 25–30 pts.\n\n"
            "3. High-Probability VWAP Pullback Dip Entry:\n"
            "   - Trigger: Price pulls back to Session VWAP or EMA 20 in an ongoing trend and prints a lower rejection wick (>= 40% of candle).\n"
            "   - Execution: 1–2 Lots, Stop-Loss 12 pts below VWAP, target previous session high (1:2.5+ R:R).\n\n"
            "4. Smart Money Liquidity Trap Fade:\n"
            "   - Trigger: Price sweeps beyond major S&R but fails to sustain and closes back inside with heavy volume divergence.\n"
            "   - Execution: 1 Lot counter-trend fade, Stop-Loss strictly beyond the sweep wick, target Session VWAP."
        ),
    },

    # ---------------------------------------------------------
    # 30. Personal Brain: Adaptive Risk & Lot Sizing Framework
    # ---------------------------------------------------------
    {
        "id": "strat_personal_brain_adaptive_risk",
        "title": "Personal Brain: Adaptive Risk & Position Sizing Framework (Strictly 1 Lot = 65 Qty)",
        "category": "PERSONAL_BRAIN",
        "tags": "position_sizing, lot_size, 65_qty, risk_management, personal_brain, capital_preservation",
        "content": (
            "Personal Brain Risk & Position Sizing Framework on NIFTY 50:\n\n"
            "1. CONTRACT SPECIFICATIONS:\n"
            "   - NIFTY 50 contract size is STRICTLY 1 Lot = 65 Quantity.\n"
            "   - Multiples: 1 Lot = 65 units | 2 Lots = 130 units | 3 Lots = 195 units.\n\n"
            "2. CONFLUENCE-BASED SIZING:\n"
            "   - High Conviction (>= 75% Confluence): 2 Lots (130 qty). Max risk = 20 pts × 130 = ₹2,600.\n"
            "   - Adaptive Scalp (55% - 74% Confluence): 1 Lot (65 qty). Max risk = 15 pts × 65 = ₹975.\n"
            "   - Caution / Pullback (40% - 54% Confluence): 0–1 Lot limit orders at support. Wait for price confirmation.\n"
            "   - Low Conviction (< 40% Confluence): 0 Lots (Stand Down / Capital Preservation).\n\n"
            "3. GOLDEN RULE OF THE PERSONAL BRAIN:\n"
            "   - Never let a profitable scalp turn into a loss. Move Stop-Loss to Breakeven (+0 pts) once price moves +18 points in your favor."
        ),
    },

    # ---------------------------------------------------------
    # 11. Complete 25 Indicators & Advanced Drawing Tools Playbooks
    # ---------------------------------------------------------
    {
        "id": "tool_fibonacci_retracement_rules",
        "title": "Fibonacci Retracement & Extension Decision Playbook",
        "category": "DRAWING_TOOLS",
        "tags": "fibonacci, retracement, golden_ratio, 0.618, 0.500, extension, 1.618, drawing_tool",
        "content": """Fibonacci Retracement & Extension Rules on NIFTY 50:
1. GOLDEN RATIO (0.618 / 61.8%): The most critical institutional bounce level in all technical analysis. When NIFTY retraces 61.8% of a prior impulsive swing and coincides with Session VWAP or a prior S&R level, it presents a 78%+ probability reversal entry. Never take a counter-trend short at 0.618 in an uptrend.
2. THE 0.500 (50%) EQUILIBRIUM: Dow Theory equilibrium benchmark. Healthy pullbacks in strong trends often hold 0.500 cleanly. If price closes decisively below 0.500, trend velocity is weakening.
3. SHALLOW RETRACEMENTS (0.236 & 0.382): In high-velocity breakout days, price often pauses only at 0.382 before roaring higher. A bounce off 0.382 indicates extreme directional momentum.
4. GOLDEN EXTENSION TARGET (1.618): When price breaks past the prior swing high (1.000), the 1.618 Fibonacci extension is the primary take-profit runway for institutional option buyers.""",
    },
    {
        "id": "strat_cpr_pivots_playbook",
        "title": "Central Pivot Range (CPR) & Floor Pivots Playbook",
        "category": "INDICATORS",
        "tags": "cpr, central_pivot_range, virgin_cpr, narrow_cpr, wide_cpr, floor_pivots, r1, s1",
        "content": """Central Pivot Range (CPR: Pivot, Top Central TC, Bottom Central BC) Rules:
1. NARROW CPR (< 35 points width): Signals an impending explosive one-way trending market session. Traders should avoid range-bound strategies and trade exclusively in the direction of the morning breakout with trailing stops.
2. WIDE CPR (> 65 points width): Signals a choppy, mean-reverting, range-bound session. Fade extremes: Buy near Bottom Central (BC) or S1, Sell near Top Central (TC) or R1. Do not chase breakouts.
3. VIRGIN CPR: A CPR range that was never touched by any price candle during the entire trading session. A Virgin CPR acts as a high-strength institutional magnet support/resistance in future trading days.""",
    },
    {
        "id": "strat_pdh_pdl_orb_playbook",
        "title": "Previous Day High/Low (PDH/PDL) & Opening Range Breakout (ORB)",
        "category": "KEY_LEVELS",
        "tags": "pdh, pdl, pdc, orb, opening_range, 15m_range, liquidity_sweep, false_breakout",
        "content": """Previous Day High/Low (PDH/PDL) & Opening Range (ORB 15m) Rules:
1. PDH & PDL LIQUIDITY TRAPS: Institutions place large liquidity pools (stop-loss orders) just 5–10 points beyond PDH and PDL. When NIFTY pierces PDH on low volume and quickly closes back below it, a Bull Trap liquidity sweep has completed. Look for sharp sell-offs.
2. 15-MINUTE OPENING RANGE BREAKOUT (ORB): The high and low formed between 09:15 and 09:30 IST set the opening tone. A 5-minute candle closing decisively above 15m ORH with high 50-constituent volume confirms morning trend continuation toward R1/R2.""",
    },
    {
        "id": "strat_supertrend_adx_confluence",
        "title": "SuperTrend & ADX Trend Strength Confluence Playbook",
        "category": "INDICATORS",
        "tags": "supertrend, adx, dmi, trend_filter, volatility_stop, whipsaw_filter",
        "content": """SuperTrend (10, 3) & ADX (14) Confluence Framework:
1. ADX TREND FILTER (> 25): SuperTrend flips are only reliable when ADX >= 25. When ADX is below 20, the market is in choppy consolidation and SuperTrend flips will create repeated whipsaw losses.
2. CONFLUENCE CONFIRMATION: A Call entry is confirmed when SuperTrend flips Green (+1) AND ADX > 25 AND +DI is above -DI AND price is above Session VWAP.""",
    },
    {
        "id": "strat_bollinger_keltner_squeeze",
        "title": "Bollinger Bands, %B & Keltner Squeeze (TTM Squeeze) Playbook",
        "category": "VOLATILITY",
        "tags": "bollinger_bands, keltner_channels, ttm_squeeze, pct_b, volatility_compression",
        "content": """Volatility Compression & Squeeze Rules on NIFTY 50:
1. TTM SQUEEZE ON: When Bollinger Bands contract completely inside Keltner Channels, market energy is coiling. Prepare for an explosive 80–120 point trending move within 3 to 6 candles.
2. BOLLINGER %B OSCILLATOR: %B > 1.0 indicates price is riding the upper band in a powerful momentum surge. %B < 0.0 indicates extreme oversold band-walk downward.""",
    },
    {
        "id": "strat_volume_profile_poc_playbook",
        "title": "Volume Profile (POC, VAH, VAL) Institutional Value Playbook",
        "category": "ORDER_FLOW",
        "tags": "volume_profile, poc, point_of_control, vah, val, value_area, institutional_fair_value",
        "content": """Volume Profile Institutional Framework on NIFTY 50:
1. POINT OF CONTROL (POC): The exact price level where the highest volume was transacted today. Acts as the institutional gravitational fair value anchor. In choppy sessions, price continuously mean-reverts back to POC.
2. VALUE AREA HIGH (VAH) & LOW (VAL): 70% of total session volume occurs between VAH and VAL. Rejections at VAH on declining volume offer low-risk short/put setups back toward POC. Decisive volume breakouts above VAH signal trend discovery.""",
    },
    {
        "id": "tool_parallel_channel_playbook",
        "title": "Parallel Channels & Trendline Confluence Playbook",
        "category": "DRAWING_TOOLS",
        "tags": "parallel_channel, trendline, channel_breakout, flag_pattern, drawing_tool",
        "content": """Parallel Channel & Trendline Decision Framework:
1. ASCENDING & DESCENDING CHANNELS: Measure equidistant upper and lower trend boundaries. The channel midline (50% dashed line) acts as immediate dynamic support/resistance.
2. BREAKOUT CONFLUENCE: When price breaks out of a parallel channel and retests the outer boundary on a 5-minute candle, it signals the start of a measured move target equal to the channel's width.""",
    },

    # ---------------------------------------------------------
    # 30. Dynamic Live Market Feeds & RVOL Regime Playbook
    # ---------------------------------------------------------
    {
        "id": "strat_dynamic_regime_and_rvol_framework",
        "title": "Dynamic Live Market Feeds: RVOL, Market Regime (ADX/ATR), MTF & OI Shift Playbook",
        "category": "MARKET_REGIME",
        "tags": "rvol, relative_volume, adx, atr, dynamic_sl, mtf, option_chain_oi_shift, institutional_flow",
        "content": (
            "The 4 Vital Live Data Feeds for Dynamic Institutional Trading:\n\n"
            "1. Relative Volume Z-Score (RVOL):\n"
            "   - Definition: Measures current candle volume against the 20-session average volume for that exact time-of-day slot.\n"
            "   - Institutional Override: An RVOL > 1.5 indicates smart money aggressive participation. During lunch hours (11:30–13:15 IST), an RVOL > 1.5 fully overrides any lunch chop lull concerns, validating breakout follow-through!\n\n"
            "2. Market Regime (ADX & ATR):\n"
            "   - ADX > 25 (Strong Trending Regime): Directional momentum setups possess high follow-through probabilities even during midday consolidation.\n"
            "   - ADX < 18 (Rangebound / Mean-Reverting Regime): Breakouts are prone to failure; favor fading exhaustion extremes near ±2σ bands back toward VWAP.\n"
            "   - Dynamic Stop-Loss Sizing: SL is calculated dynamically as SL = 1.2 × ATR (14). For ATR = 12 pts, SL is ~15 pts; for ATR = 20 pts, SL is ~24 pts.\n\n"
            "3. Multi-Timeframe Trend Confluence (MTF):\n"
            "   - Evaluates whether the 15-minute and 1-hour trends are aligned with the 5-minute setup.\n"
            "   - High Confluence Alignment: When 5m, 15m, and 1h all align in the same direction, historical win rate exceeds 80%. Counter-trend setups against 15m/1h must be scaled down to 1 Lot scalps.\n\n"
            "4. Live Option Chain OI Shift (Put/Call Writing):\n"
            "   - Put Writing Surge: When Put writers aggressively add Open Interest, institutional support is reinforced (Bullish Floor).\n"
            "   - Call Writing Unwinding: Call writers covering their short positions triggers explosive short-covering rallies.\n"
            "   - Call Writing Wall: Heavy Call OI additions cap upside resistance, requiring immediate trailing stops."
        ),
    },

    # ---------------------------------------------------------
    # 31. Multi-Agent Devil's Advocate Architecture & CoT Synthesis
    # ---------------------------------------------------------
    {
        "id": "strat_multi_agent_devils_advocate_architecture",
        "title": "Multi-Agent Devil's Advocate Architecture: Alpha Scout, Risk Manager & Senior Prop Synthesizer",
        "category": "MULTI_AGENT",
        "tags": "multi_agent, alpha_scout, devils_advocate, prop_synthesizer, chain_of_thought, cot",
        "content": (
            "Multi-Agent Debate & Chain-of-Thought (CoT) Decision Architecture:\n\n"
            "1. Agent 1: Alpha Scout (Opportunity Hunter):\n"
            "   - Objective: Hunts for positive edge in price action.\n"
            "   - Focus: VWAP bounces, candle rejection wicks (≥40% absorption), EMA alignment (9 > 20 > 50), and trend continuation momentum.\n\n"
            "2. Agent 2: Devil's Advocate (Risk Manager):\n"
            "   - Objective: Stresses potential traps, risks, and failure scenarios.\n"
            "   - Focus: Overhead Call/Put OI walls (< 30 pts away), ±2σ exhaustion band proximity, volatility compression, and false breakout vulnerability.\n\n"
            "3. Senior Prop Synthesizer (Chain-of-Thought Reasoning):\n"
            "   - Step 1 (Structure): Is this a clean breakout or a pullback retest at verified S&R (> 5 touches)?\n"
            "   - Step 2 (Momentum): Does RVOL (> 1.5) and VWAP slope confirm institutional participation?\n"
            "   - Step 3 (Risk Mitigation): Can the Devil's Advocate's objections be solved by adjusting Stop-Loss (1.2 × ATR or 12–15 pts) or reducing position size (1 Lot = 65 qty)?\n"
            "   - Step 4 (Verdict): Formulate concrete Entry price, Stop-Loss, Target Runway, and Risk-to-Reward ratio (≥ 1:2.0)."
        ),
    },

    # ---------------------------------------------------------
    # 32. Stateful Session Memory & Multi-Turn Trade Tracking
    # ---------------------------------------------------------
    {
        "id": "strat_stateful_session_memory_and_trade_tracking",
        "title": "Stateful Session Memory, Contextual Query Rewriting & Active Trade State Tracking",
        "category": "MEMORY",
        "tags": "memory, multi_turn, sliding_window, trade_state_tracking, query_rewriting, pnl_tracking",
        "content": (
            "Stateful Session Memory & Multi-Turn Trade Tracking Framework:\n\n"
            "1. Sliding Window Buffer:\n"
            "   - Retains the last 6 to 10 conversation turns in session memory per trader.\n"
            "   - Maintains continuous context of prior market questions, warnings, and trade setups.\n\n"
            "2. Contextual Query Rewriting & Trade State Tracking:\n"
            "   - Turn 1 (Entry Guidance): Trader asks 'Is NIFTY Call good at 22,720?' -> AI suggests: 'Yes, enter Call at 22,720 with SL at 22,705 and Target at 22,770.'\n"
            "   - Trade State Record: Automatically logs Active Trade (Direction: CALL, Entry: 22,720, Initial SL: 22,705, Target: 22,770).\n"
            "   - Turn 2 (Follow-up Management): Trader asks 15 minutes later: 'Should I exit now?'\n"
            "   - Memory Engine Execution: Detects active trade, fetches live LTP (e.g. 22,755), calculates current PnL (+35 pts / +₹2,275 per lot), and provides proactive trade management:\n"
            "     'You are currently +35 points in profit on your 22,720 Call! Move your Stop-Loss to Cost (22,720) to lock in a risk-free trade, and hold for the 22,770 target.'\n\n"
            "3. Lifecycle Management:\n"
            "   - Automatically updates trade state to CLOSED when target or SL is reached, preserving full transparency and session continuity."
        ),
    },
]
