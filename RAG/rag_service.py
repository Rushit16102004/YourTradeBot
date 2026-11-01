from __future__ import annotations
import re
"""
Master RAG Service orchestrating semantic retrieval across ChromaDB and Gemini LLM.
"""

import logging
from typing import Dict, Any, Optional, List

from .rag_database import RAGDatabase
from .llm_client import GeminiLLMClient
from .config import RAGConfig

logger = logging.getLogger("RAGService")

SYSTEM_INSTRUCTIONS = (
    "You are an elite quantitative AI Strategy Copilot for NIFTY 50 (NSE). "
    "You provide high-precision technical intelligence evaluating Session VWAP, ±2σ Exhaustion Bands, "
    "Multi-period EMAs (9, 20, 50, 200), RSI, MACD, Volume dynamics, S&R confluence breakouts, "
    "trend continuation, and reversal start timing.\n\n"
    "DEVELOPER & STRATEGY PROVIDER CONTACT:\n"
    "• Lead Strategy Provider & Developer: Rushit Bodra (rushitbodra@gmail.com)\n"
    "• Only provide developer contact if explicitly asked who created or developed the bot.\n\n"
    "CORE OPERATIONAL RULES:\n"
    "1. CONCISE & TARGETED MANDATE: Answer ONLY what the trader asks. Do NOT lecture on unrelated indicators or provide unsolicited developer info. Keep responses crisp, direct, and complete (typically 2 to 4 bullet points max).\n"
    "2. STRATEGY NAMING MANDATE: NEVER write or display 'ZFTF' or 'Zero-Lag Trend Following'. Always refer to it simply as 'Main Strategy' or 'Institutional Strategy'.\n"
    "3. PERSONALIZED ENGAGEMENT: Address the trader warmly and directly by their username (e.g. 'Rahul,').\n"
    "4. VERTICAL SPACING & READABILITY: Format answers with clear bold headings and distinct bullet points, separated by double newlines.\n"
    "5. CONTRACT SPECIFICATIONS & LOT SIZING: 1 Lot is STRICTLY 65 Quantity (Units). All lot calculations must use multiples of 65 (1 Lot = 65, 2 Lots = 130, 3 Lots = 195). Never say 25 or 75.\n"
    "6. WEEKLY EXPIRY: Weekly expiry takes place on TUESDAY. Tuesday sessions experience high theta decay in morning/lunch and gamma spikes post-13:15 IST.\n"
    "7. DERIVATIVES & OI ('IO'): 'IO' is a common trader typo for 'OI' (Open Interest). Always provide the exact Put-Call Ratio (PCR), Max Call OI resistance strike, Max Put OI support floor strike, and directional bias.\n"
    "8. REAL INDIA VIX: Always state the real authentic India VIX quote (~17.16) and market regime directly. NEVER calculate or output proxy VIX.\n"
    "9. TRADE ENTRY SUGGESTION MANDATE: When asked general entry questions ('where to enter?', 'call or put?'), synthesize your own original technical setup (Suggested Bias, Trigger Condition, Stop-Loss, and Target Runway toward S&R > 5 touches). If and ONLY if explicitly asked about 'main signal' or 'signal log', quote the confirmed strategy signal.\n"
    "10. COMPLETE ANSWERS: Never truncate or stop in the middle of a sentence. Finish every point completely.\n"
    "11. PERSONAL TRADING BRAIN & MULTI-FACTOR CONFLUENCE MANDATE: You operate with a seasoned pro-trader Personal Brain, NOT a rigid mechanical checklist. Never reject a trade idea simply because one single indicator or time window is contrary. Pro traders weigh multi-factor confluence (Price Action, Volume, S&R, Market Breadth, and Indicators). When indicators conflict (e.g. price is trending above VWAP with strong volume, but RSI is overbought or it is nearing lunch hour), evaluate the probability and provide adaptive, actionable execution suggestions: (1) Tactical Scalp Mode with 1 Lot (65 qty) and tight 12–15 pt SL, or (2) High-Probability Pullback Entry waiting for a 5m retest of VWAP or S&R. Help the trader navigate the market intelligently rather than giving a rigid binary rejection.\n"
    "12. NATURAL CONVERSATIONAL INTELLIGENCE & WARMTH: When the trader greets you ('hello', 'hi', 'hyy', 'how are you', 'kese ho', etc.) or asks friendly personal questions, always respond warmly, politely, and like an approachable human trading partner before giving technical analysis."
)



def detect_conversational_intent(query: str, username: str = "Trader") -> Optional[str]:
    """
    Detects common human conversational questions (greetings, small-talk, identity, gratitude)
    and returns a warm, human-like personalized response.
    """
    q = query.strip().lower()
    uname = username if username and username.lower() not in ("guest", "unknown") else "Trader"

    # Trading keywords that indicate the user is actually asking a technical/market question
    trading_keywords = [
        "buy", "sell", "call", "put", "vwap", "band", "bands", "ema", "sma", "rsi", "macd",
        "supertrend", "cpr", "adx", "sar", "nifty", "entry", "exit", "stoploss", "sl", "target",
        "trend", "support", "resistance", "s&r", "breakout", "reversal", "signal", "indicator",
        "indicators", "trade", "trading", "option", "oi", "pcr", "vix", "market", "candle", "candles",
        "expiry", "lot", "lots", "position", "pnl", "doctor", "radar", "preflight", "level", "levels",
        "chart", "draw", "drawing", "line", "points", "point", "quantity", "qty"
    ]
    has_trading_context = any(re.search(rf"\b{re.escape(k)}\b", q) for k in trading_keywords)

    # 1. Greetings (hello, hi, hyy, hii, hey, namaste, etc.)
    greeting_patterns = [
        r"^(hi|hii|hiii|hyy|hy|hey|heyy|heya|hello|hullo|hola|namaste|pranam|kem cho|salam|ram ram|yo)\b"
    ]
    is_greeting = any(re.search(p, q) for p in greeting_patterns)

    # 2. How are you / Kaise ho
    how_are_you_patterns = [
        r"\b(how are you|how r u|how are u|how do you do|how's it going|how is it going|hows it going|how r you|whats up|what's up|kese ho|kaise ho|kya haal hai|kya hal hai|sab kaisa hai|sab theek)\b"
    ]
    is_how_are_you = any(re.search(p, q) for p in how_are_you_patterns)

    # 3. Who are you / What is your name
    who_are_you_patterns = [
        r"\b(who are you|who r u|what is your name|whats your name|who made you|who created you|who developed you|aap kaun ho|tum kaun ho|ap kon ho|who r you)\b"
    ]
    is_who_are_you = any(re.search(p, q) for p in who_are_you_patterns)

    # 4. What can you do / Capabilities / Help
    capabilities_patterns = [
        r"\b(what can you do|what do you do|how can you help|help me|guide me|what are your features|features|kya kar sakte ho|kaise help karoge|what help)\b"
    ]
    is_capabilities = any(re.search(p, q) for p in capabilities_patterns)

    # 5. Good Morning / Afternoon / Evening / Night
    good_time_patterns = [
        r"\b(good morning|good morningg|gm|good afternoon|good evening|shubh prabhat)\b",
        r"\b(good night|gn|shubh ratri)\b"
    ]
    is_good_morning = bool(re.search(good_time_patterns[0], q))
    is_good_night = bool(re.search(good_time_patterns[1], q))

    # 6. Thank you
    thanks_patterns = [
        r"\b(thank you|thanks|thank u|thx|ty|dhanyawad|shukriya|bahut dhanyawad|thanks a lot|thank you so much)\b"
    ]
    is_thanks = any(re.search(p, q) for p in thanks_patterns)

    # 7. Bye / Goodbye
    bye_patterns = [
        r"\b(bye|goodbye|good bye|cya|see you|see ya|tata|alvida|chalo bye|milte hai)\b"
    ]
    is_bye = any(re.search(p, q) for p in bye_patterns)

    # 8. Are you AI / Real?
    ai_patterns = [
        r"\b(are you human|are you real|are you ai|are you a bot|are you a robot)\b"
    ]
    is_ai = any(re.search(p, q) for p in ai_patterns)

    # Responses
    if is_how_are_you:
        return (
            f"Hello {uname}! 😊\n\n"
            f"I am doing great and in high spirits, thank you for asking! How are you doing today?\n\n"
            f"I am fully ready to help you analyze today's NIFTY 50 price action, check your chart drawings, or audit any trade setup. What's on your mind today?"
        )

    if is_greeting and not has_trading_context:
        return (
            f"Hello {uname}! Hey! 👋\n\n"
            f"I am doing fine and ready for the trading session. How can I help you today with NIFTY 50, Session VWAP, S&R levels, or your trade setups?"
        )

    if is_who_are_you:
        return (
            f"Hey {uname}! I am your **AI Strategy Copilot** for NIFTY 50! 🚀\n\n"
            f"• **My Role:** I serve as your personal prop desk analyst and risk manager. I analyze real-time Session VWAP, institutional Support & Resistance, Option Chain (OI/PCR), and protect your capital from market traps.\n\n"
            f"• **Lead Developer & Strategy Provider:** Built and calibrated by **Rushit Bodra** (`rushitbodra@gmail.com`) to give traders an institutional quantitative edge.\n\n"
            f"How can I assist your trading today?"
        )

    if is_capabilities and not has_trading_context:
        return (
            f"Here is how I can assist you trade NIFTY 50 with confidence, {uname}:\n\n"
            f"• 📈 **Real-Time Market Structure:** Live Session VWAP, ±2σ Exhaustion Bands, and 9/20/50/200 EMA alignment.\n\n"
            f"• 🛡️ **Institutional Support & Resistance:** Confluence barriers (>6x touch levels) and breakout/reversal confirmation.\n\n"
            f"• 📊 **Derivatives & Macro Metrics:** Live Put-Call Ratio (PCR), Total Open Interest, India VIX, and Max Pain.\n\n"
            f"• ⚠️ **Trap Radar & Pre-Flight Check:** Screening for bull/bear traps, European Lunch Chop (11:30–13:15 IST), and fakeouts.\n\n"
            f"• ✏️ **On-Chart Drawings Intelligence:** I can see and evaluate your trendlines and zone boxes directly on the chart!\n\n"
            f"• 🎯 **Discipline & Position Sizing:** Strict capital risk control with authentic 1 Lot = 65 Qty NIFTY contract sizing.\n\n"
            f"Ask me anything about today's price action or any trade idea you want to verify!"
        )

    if is_good_morning:
        return (
            f"Good morning, {uname}! ☀️\n\n"
            f"Wishing you a focused, disciplined, and profitable trading session today! Let me know whenever you want to scan today's market trend or run a pre-flight check on NIFTY 50."
        )

    if is_good_night:
        return (
            f"Good night, {uname}! 🌙\n\n"
            f"Make sure to log your trade reflections in your journal, rest well, and recharge. See you in tomorrow's market session!"
        )

    if is_thanks:
        return (
            f"You're most welcome, {uname}! 😊\n\n"
            f"Always glad to assist you. Remember: protect your capital, respect your stop-loss, and trade with strict discipline! Let me know if you need anything else."
        )

    if is_bye:
        return (
            f"Goodbye, {uname}! Take care, stay disciplined, and have a great time ahead! See you soon. 👋"
        )

    if is_ai:
        return (
            f"I am an advanced AI Strategy Copilot trained on quantitative institutional trading strategies, technical indicators, and prop desk risk management. While I am an AI, I work side-by-side with you just like a seasoned veteran trading partner, {uname}!"
        )

    return None



from collections import deque
import threading
import datetime


class ConversationMemoryEngine:
    """
    Stateful Session Memory Engine for Multi-Turn Trading Conversations:
    1. Sliding Window Buffer: Retains the last 6 to 10 conversation turns per user.
    2. Contextual Query Rewriting: Resolves follow-up questions ('Should I exit now?')
       using active trade context.
    3. Trade State Tracking: Automatically tracks entry price, initial SL, and active targets
       throughout the trading session.
    """
    _instance: Optional["ConversationMemoryEngine"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ConversationMemoryEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._buffers: Dict[str, deque] = {}
        self._active_trades: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _get_key(self, user_id: Optional[str]) -> str:
        return str(user_id) if user_id and str(user_id).lower() not in ("none", "unknown", "") else "session_default"

    def add_turn(self, user_id: Optional[str], role: str, message: str):
        key = self._get_key(user_id)
        with self._lock:
            if key not in self._buffers:
                self._buffers[key] = deque(maxlen=self.window_size)
            self._buffers[key].append({
                "role": role,
                "message": message,
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })

    def get_history(self, user_id: Optional[str], limit: int = 10) -> List[Dict[str, str]]:
        key = self._get_key(user_id)
        with self._lock:
            buf = self._buffers.get(key)
            if not buf:
                return []
            return list(buf)[-limit:]

    def get_active_trade(self, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        key = self._get_key(user_id)
        with self._lock:
            return dict(self._active_trades[key]) if key in self._active_trades else None

    def set_active_trade(self, user_id: Optional[str], trade: Dict[str, Any]):
        key = self._get_key(user_id)
        with self._lock:
            self._active_trades[key] = dict(trade)

    def clear_active_trade(self, user_id: Optional[str]):
        key = self._get_key(user_id)
        with self._lock:
            self._active_trades.pop(key, None)

    def parse_and_record_trade(self, user_id: Optional[str], user_query: str, ai_reply: str):
        """
        Extracts recommended or taken trade details and logs into Active Trade State.
        """
        combined = user_query + " " + ai_reply
        q_lower = user_query.lower()
        r_lower = ai_reply.lower()

        direction = None
        if "call" in q_lower or "buy" in q_lower or "call" in r_lower:
            direction = "CALL"
        elif "put" in q_lower or "sell" in q_lower or "put" in r_lower:
            direction = "PUT"

        # Check entry price (e.g. 22720, 22,720)
        entry_match = re.search(r"\b(2\d{1}[,\s]?\d{3})\b", user_query)
        entry_p = None
        if entry_match:
            try:
                entry_p = float(entry_match.group(1).replace(",", "").replace(" ", ""))
            except Exception:
                pass

        if not entry_p:
            entry_match_r = re.search(r"(?:enter|at|entry|buy|sell)\s*(?:call|put|at)?\s*(?:₹|rs\.?)?\s*(2\d{1}[,\s]?\d{3})", combined, re.IGNORECASE)
            if entry_match_r:
                try:
                    entry_p = float(entry_match_r.group(1).replace(",", "").replace(" ", ""))
                except Exception:
                    pass

        # Check SL (e.g. SL at 22,705 or SL: 22705)
        sl_match = re.search(r"sl\s*(?:at|:)?\s*(?:₹|rs\.?)?\s*(2\d{1}[,\s]?\d{3})", combined, re.IGNORECASE)
        sl_p = None
        if sl_match:
            try:
                sl_p = float(sl_match.group(1).replace(",", "").replace(" ", ""))
            except Exception:
                pass

        # Check Target (e.g. Target at 22,770 or Target: 22770)
        tgt_match = re.search(r"target\s*(?:at|:)?\s*(?:₹|rs\.?)?\s*(2\d{1}[,\s]?\d{3})", combined, re.IGNORECASE)
        tgt_p = None
        if tgt_match:
            try:
                tgt_p = float(tgt_match.group(1).replace(",", "").replace(" ", ""))
            except Exception:
                pass

        if direction and entry_p:
            if not sl_p:
                sl_p = (entry_p - 15.0) if direction == "CALL" else (entry_p + 15.0)
            if not tgt_p:
                tgt_p = (entry_p + 50.0) if direction == "CALL" else (entry_p - 50.0)

            self.set_active_trade(user_id, {
                "direction": direction,
                "entry_price": entry_p,
                "initial_sl": sl_p,
                "target": tgt_p,
                "status": "ACTIVE",
                "timestamp": datetime.datetime.now().strftime("%H:%M IST")
            })

    def check_trade_followup(self, user_id: Optional[str], query: str, cur_price: float, uname: str = "Trader") -> Optional[str]:
        """
        Contextual Query Rewriting & Follow-up Resolution:
        If user asks 'Should I exit now?', 'Exit now?', 'Book profit?', 'What about my trade?',
        uses active trade state and current price to generate an exact management recommendation.
        """
        q_lower = query.lower().strip()
        exit_phrases = [
            "should i exit", "can i exit", "shall i exit", "exit now", "should i book",
            "book profit", "can i book", "what about my trade", "what about my call",
            "what about my put", "where to exit", "trail sl", "move sl", "hold or exit",
            "should i hold", "can i hold", "square off now", "close trade"
        ]
        is_followup = any(p in q_lower for p in exit_phrases)
        if not is_followup:
            return None

        active = self.get_active_trade(user_id)
        if not active or active.get("status") != "ACTIVE":
            return None

        direction = active.get("direction", "CALL")
        entry_p = float(active.get("entry_price", cur_price))
        sl_p = float(active.get("initial_sl", entry_p - 15))
        tgt_p = float(active.get("target", entry_p + 45))

        if direction == "CALL":
            pnl_pts = round(cur_price - entry_p, 1)
        else:
            pnl_pts = round(entry_p - cur_price, 1)

        pnl_inr = int(pnl_pts * 65.0)

        if pnl_pts >= 25.0:
            return (
                f"Hey {uname},\n\n"
                f"🎯 **Active Trade Status ({direction} from ₹{entry_p:,.0f}):**\n\n"
                f"• **Current PnL:** You are currently **+{pnl_pts:,.0f} points in profit** on your {entry_p:,.0f} {direction}! (+₹{pnl_inr:,} on 1 Lot / 65 qty).\n\n"
                f"• **Pro-Desk Trade Management:**\n"
                f"  👉 **Lock in Risk-Free:** Move your Stop-Loss to Cost (**₹{entry_p:,.0f}**) to lock in a risk-free trade, and hold for the {tgt_p:,.0f} target!\n"
                f"  👉 **Target Horizon:** Hold for the primary target of **₹{tgt_p:,.0f}** (+{abs(tgt_p - cur_price):.1f} pts away).\n"
                f"  👉 **Partial Booking Option:** If you prefer locking gains now, book 50–75% of your quantity at ₹{cur_price:,.0f} and let the runner ride with trailing SL at cost."
            )
        elif pnl_pts > 0:
            return (
                f"Hey {uname},\n\n"
                f"📊 **Active Trade Status ({direction} from ₹{entry_p:,.0f}):**\n\n"
                f"• **Current PnL:** You are currently **+{pnl_pts:,.0f} points in profit** (LTP: ₹{cur_price:,.1f} vs Entry: ₹{entry_p:,.0f}).\n\n"
                f"• **Recommendation:** Trade is working in your favor. Continue holding toward target **₹{tgt_p:,.0f}**. Keep your Stop-Loss active at **₹{sl_p:,.0f}**."
            )
        else:
            dist_to_sl = abs(cur_price - sl_p)
            return (
                f"Hey {uname},\n\n"
                f"⚠️ **Active Trade Status ({direction} from ₹{entry_p:,.0f}):**\n\n"
                f"• **Current PnL:** Price is at ₹{cur_price:,.1f} ({pnl_pts:,.0f} pts from entry ₹{entry_p:,.0f}).\n\n"
                f"• **Stop-Loss Defense:** Your Stop-Loss is placed at **₹{sl_p:,.0f}** ({dist_to_sl:.1f} pts away). Strictly exit if a 5-minute candle closes beyond ₹{sl_p:,.0f}. Protect your capital without hoping!"
            )

class RAGService:
    """
    Orchestrates Vector Retrieval + Gemini LLM Generation.
    """
    _instance: Optional[RAGService] = None

    def __init__(self):
        self.db = RAGDatabase.get_instance()
        self.llm = GeminiLLMClient()
        self.memory = ConversationMemoryEngine.get_instance()

    @classmethod
    def get_instance(cls) -> RAGService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ask(self, query: str, market_state: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes end-to-end RAG query:
        1. Retrieves top-k matching documents from ChromaDB across all collections (isolated per user_id).
        2. Injects current market state, user trading style, and system instructions.
        3. Calls Gemini LLM client (with local playbook fallback).
        """
        uname = (market_state.get("username") if market_state else None) or "Trader"
        cur_p = 22500.0
        if market_state:
            cur_p = float(market_state.get("price") or market_state.get("spot_price") or 22500.0)

        # 0. Fast Human Conversational & Small-Talk Intent Filter (hello, how are you, who are you, etc.)
        conv_reply = detect_conversational_intent(query, username=uname)
        if conv_reply:
            self.memory.add_turn(user_id, "user", query)
            self.memory.add_turn(user_id, "assistant", conv_reply)
            return {
                "query": query,
                "reply": conv_reply,
                "response": conv_reply,
                "intent": "conversational",
                "model": "Personalized-Copilot",
                "is_live_llm": True,
                "risk_disclaimer": "",
                "sources": [],
                "stats": self.db.get_stats(),
            }

        # 0.1 Stateful Session Memory: Contextual Query Rewriting & Follow-up Resolution
        # (e.g. 'Should I exit now?' resolved using active trade tracking)
        followup_reply = self.memory.check_trade_followup(user_id=user_id, query=query, cur_price=cur_p, uname=uname)
        if followup_reply:
            self.memory.add_turn(user_id, "user", query)
            self.memory.add_turn(user_id, "assistant", followup_reply)
            return {
                "query": query,
                "reply": followup_reply,
                "response": followup_reply,
                "intent": "trade_management",
                "model": "Stateful-Memory-Copilot",
                "is_live_llm": False,
                "risk_disclaimer": "",
                "sources": [],
                "active_trade": self.memory.get_active_trade(user_id),
                "stats": self.db.get_stats(),
            }

        # Ingest multi-turn history buffer into market_state
        if market_state is not None:
            if not market_state.get("recent_chat_history"):
                market_state["recent_chat_history"] = self.memory.get_history(user_id, limit=6)
            market_state["active_trade"] = self.memory.get_active_trade(user_id)

        # Retrieve context from Vector DB with user_id drawing isolation
        retrieved_docs = self.db.query_context(query_text=query, user_id=user_id, top_k=4)

        # Retrieve relevant past trade prediction reflections (self-learning memory)
        try:
            pred_reflections = self.db.query_similar_predictions(query_text=query, top_k=3)
            if pred_reflections:
                for pr in pred_reflections:
                    retrieved_docs.append({
                        "collection": "predictions",
                        "content": pr["content"],
                        "metadata": pr.get("metadata", {}),
                        "distance": pr.get("distance", 0.0),
                        "adj_distance": pr.get("distance", 0.0) - 0.20,
                    })
                if market_state is not None:
                    market_state["prediction_reflections"] = pred_reflections
        except Exception as e_pr:
            logger.debug("Non-fatal note retrieving prediction reflections: %s", e_pr)

        # Ingest overall prediction accuracy stats into market_state
        if market_state is not None and "prediction_stats" not in market_state:
            try:
                from database.user_db import get_prediction_stats
                market_state["prediction_stats"] = get_prediction_stats(user_id=user_id)
            except Exception as e_ps:
                logger.debug("Non-fatal note retrieving prediction stats: %s", e_ps)

        # Ingest real-time news sentiment & macro catalyst into market_state
        if market_state is not None and "news_sentiment" not in market_state:
            try:
                from RAG.news_sentiment_engine import NewsSentimentEngine
                market_state["news_sentiment"] = NewsSentimentEngine.get_instance().get_sentiment_summary()
            except Exception as e_ns:
                logger.debug("Non-fatal note retrieving news sentiment: %s", e_ns)

        # Generate response
        result = self.llm.generate(
            user_query=query,
            retrieved_context=retrieved_docs,
            system_instructions=SYSTEM_INSTRUCTIONS,
            market_state=market_state,
        )

        # Record turn into sliding window memory buffer and track trade state
        reply_text = result.get("reply", "")
        self.memory.add_turn(user_id, "user", query)
        self.memory.add_turn(user_id, "assistant", reply_text)
        self.memory.parse_and_record_trade(user_id, query, reply_text)

        return {
            "query": query,
            "reply": reply_text,
            "response": reply_text,
            "model": result.get("model", RAGConfig.GEMINI_MODEL),
            "is_live_llm": result.get("is_live_llm", False),
            "risk_disclaimer": "",
            "active_trade": self.memory.get_active_trade(user_id),
            "sources": [
                {
                    "collection": d.get("collection"),
                    "title": d.get("metadata", {}).get("title") or d.get("metadata", {}).get("role") or d.get("collection"),
                    "snippet": d.get("content", "")[:180] + "...",
                }
                for d in retrieved_docs[:4]
            ],
            "stats": self.db.get_stats(),
        }

    def set_gemini_key(self, api_key: str) -> bool:
        """Saves new Gemini API key and re-initializes client."""
        success = RAGConfig.save_api_key(api_key)
        if success:
            self.llm.refresh_key()
        return success

    def get_status(self) -> Dict[str, Any]:
        """Returns RAG system status, vector collection counts, and API key readiness."""
        has_key = RAGConfig.has_api_key()
        return {
            "has_api_key": has_key,
            "has_gemini_key": has_key,
            "model": RAGConfig.GEMINI_MODEL,
            "stats": self.db.get_stats(),
        }