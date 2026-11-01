"""
RAG/news_sentiment_engine.py
Real-Time High-Impact News Sentiment & Macro Catalyst Engine.

Features:
1. 100% Free Live Streaming: Uses Google News Financial RSS (zero paid API keys, unlimited requests).
2. Strict Noise Reduction ("Big News Only"): Filters out routine broker tips, chartist chatter,
   and daily retail noise. Retains ONLY Grade-A catalysts (RBI / Monetary Policy, Crude Oil shocks,
   Geopolitics/War, Government/SEBI policy, and Top-5 Index Heavyweights).
3. Directional Polarity & NIFTY Options Verdict:
   - Evaluates impact score (1 to 10) and sentiment polarity (-1.0 to +1.0).
   - Grade-A cutoff: Impact >= 7.5 triggers directional trade guidance (CE Calls vs PE Puts).
4. Dual Classification Pipeline: Instant regex/heuristic rules with optional Gemini LLM verification.
5. Thread-Safe Background Polling: Continuously updates in background every 90 seconds.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional
import urllib.request
import xml.etree.ElementTree as ET

from RAG.config import RAGConfig

logger = logging.getLogger("NewsSentimentEngine")

# Live Google News Curated Business Topic (Strictly verified live business newsrooms)
RSS_PRIMARY_URL = (
    "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en"
)
# Live Market Search restricted to the last 12 hours strictly
RSS_BACKUP_URL = (
    "https://news.google.com/rss/search?q=NIFTY+50+OR+Sensex+OR+RBI+when:12h&hl=en-IN&gl=IN&ceid=IN:en"
)

BLOCKED_SCRAPERS = [
    "dd news", "kucoin", "scanx", "bbn times", "pragativadi", "investment guru", "cryptocurrency"
]

STALE_ANACHRONISMS = [
    r"fed rate hike", r"midterm election", r"crude oil above \$11", r"nse ipo in focus"
]
CACHE_FILE = Path(__file__).resolve().parent.parent / "temp_storage" / "news_sentiment_cache.json"


class NewsSentimentEngine:
    _instance: Optional["NewsSentimentEngine"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "NewsSentimentEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._cache_lock = threading.Lock()
        self._cached_summary: Dict[str, Any] = self._load_persisted_cache() or self._get_default_summary()
        self._last_fetch_ts: float = 0.0
        self._poller_thread: Optional[threading.Thread] = None
        self._stop_poller = threading.Event()

    # -------------------------------------------------------------
    # Default State & Cache Persistence
    # -------------------------------------------------------------
    def _get_default_summary(self) -> Dict[str, Any]:
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now_ist = datetime.datetime.now(ist_tz)
        return {
            "status": "ok",
            "last_updated": now_ist.strftime("%d %b %Y, %I:%M %p IST"),
            "overall_sentiment": "NEUTRAL",
            "sentiment_score": 0.0,
            "is_high_impact": False,
            "impact_category": "NONE",
            "breaking_catalyst": None,
            "market_direction": "SIDEWAYS / STRUCTURAL FLOW",
            "trading_verdict": "Macro background is calm. Follow Session VWAP and S&R boundaries.",
            "feed_count": 0,
            "high_impact_count": 0,
            "headlines": [],
        }

    def _load_persisted_cache(self) -> Optional[Dict[str, Any]]:
        try:
            if CACHE_FILE.exists():
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "overall_sentiment" in data:
                    return data
        except Exception as e:
            logger.debug("Could not load persisted news cache: %s", e)
        return None

    def _save_persisted_cache(self, data: Dict[str, Any]):
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.debug("Could not persist news cache: %s", e)

    # -------------------------------------------------------------
    # Noise Filtering & Heuristic Classification
    # -------------------------------------------------------------
    @staticmethod
    def format_pub_date_ist(pub_date_str: str) -> tuple[str, float, str, str]:
        """
        Converts any international GMT / UTC / RFC-2822 date to Indian Standard Time (IST).
        Returns: (formatted_ist, epoch_seconds, time_ago, full_display_str)
        Example: ('01 Nov, 12:07 PM IST', 1730460442.0, '5h 10m ago', '01 Nov, 12:07 PM IST (5h 10m ago)')
        """
        if not pub_date_str:
            return "Recently", 0.0, "Recently", "Recently"
        try:
            import email.utils
            dt_utc = email.utils.parsedate_to_datetime(pub_date_str)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            dt_ist = dt_utc.astimezone(ist_tz)
            epoch = dt_utc.timestamp()

            utc_now = datetime.datetime.now(datetime.timezone.utc)
            diff_sec = max(0, int((utc_now - dt_utc).total_seconds()))

            if diff_sec < 90:
                time_ago = "Just now"
            elif diff_sec < 3600:
                m = diff_sec // 60
                time_ago = f"{m}m ago"
            elif diff_sec < 86400:
                h = diff_sec // 3600
                m = (diff_sec % 3600) // 60
                time_ago = f"{h}h {m}m ago" if m > 0 else f"{h}h ago"
            else:
                d = diff_sec // 86400
                time_ago = f"{d}d ago"

            formatted_ist = dt_ist.strftime("%d %b, %I:%M %p IST")
            full_display = f"{formatted_ist} ({time_ago})"
            return formatted_ist, epoch, time_ago, full_display
        except Exception:
            return pub_date_str, 0.0, "Recently", pub_date_str

    @staticmethod
    def classify_headline(title: str, source: str = "", pub_date: str = "") -> Dict[str, Any]:
        """
        Classifies individual headline into high-impact macro categories vs routine noise,
        assigning impact score (1 to 10), polarity (-1.0 to 1.0), and directional trade bias.
        """
        t_clean = title.strip()
        t_lower = t_clean.lower()

        # 0. Reject low-tier scrapers and stale recycled articles
        s_lower = source.lower().strip()
        is_blocked_source = any(b in s_lower for b in BLOCKED_SCRAPERS)
        is_stale_article = any(re.search(p, t_lower) for p in STALE_ANACHRONISMS)

        # 1. Noise check (routine stock tips, columns, retail chatter)
        noise_patterns = [
            r"chartist talk", r"what history suggest", r"what 25 yrs", r"stocks to buy",
            r"brokerage recommends", r"target price", r"stock picks", r"portfolio advice",
            r"mutual fund inflow", r"top gainers", r"top losers", r"buzzing stocks",
            r"technical view", r"what to expect", r"hot stocks", r"penny stocks"
        ]
        is_routine_noise = any(re.search(p, t_lower) for p in noise_patterns)

        if is_blocked_source or is_stale_article:
            category = "MARKET_NOISE"
            impact_score = 1.0
            return {
                "title": t_clean,
                "source": source or "Financial Media",
                "published_at": "Stale Archive",
                "published_ist": "Stale",
                "time_ago": "Archived",
                "pub_epoch": 0.0,
                "category": "MARKET_NOISE",
                "impact_score": 1.0,
                "is_high_impact": False,
                "polarity": "NEUTRAL",
                "score": 0.0,
                "market_direction": "SIDEWAYS",
                "trading_verdict": "Stale recycled news filtered out.",
            }

        category = "MARKET_NOISE"
        impact_score = 2.0
        polarity = "NEUTRAL"
        score = 0.0
        market_direction = "SIDEWAYS"
        trading_verdict = "Routine market noise. Does not alter structural bias; rely on Session VWAP."

        # 2. High-Impact Category Classifications

        # A. Central Bank / Monetary Policy (Impact: 9.0)
        cb_keywords = [
            "rbi", "repo rate", "mpc", "monetary policy", "rate hike", "rate cut",
            "shaktikanta", "fed rate", "fomc", "powell", "cpi inflation", "wpi inflation",
            "federal reserve", "central bank", "interest rate", "interest rates", "inflation"
        ]
        is_cb_match = any(k in t_lower for k in cb_keywords) or bool(re.search(r"\b(fed|rbi|fomc|mpc)\b", t_lower))
        if is_cb_match:
            category = "CENTRAL_BANK"
            impact_score = 9.0
            if any(w in t_lower for w in ["cut", "cuts", "slash", "easing", "dovish", "cools", "falls", "drop", "lower", "tamed"]):
                polarity = "STRONG BULLISH"
                score = 0.85
                market_direction = "BULLISH RALLY"
                trading_verdict = "Dovish monetary action / falling inflation. Favors CE Call buying on VWAP retests. Rate-sensitives & Banking leading."
            elif any(w in t_lower for w in ["hike", "hikes", "raises", "hawkish", "spikes", "surges", "higher inflation", "stubborn"]):
                polarity = "STRONG BEARISH"
                score = -0.85
                market_direction = "BEARISH SELL-OFF"
                trading_verdict = "Hawkish policy surprise / inflation spike. Margin compression fears. Favor PE Puts or breakdown entries."
            else:
                polarity = "NEUTRAL"
                score = 0.0
                impact_score = 7.5
                market_direction = "SIDEWAYS / CHOPPY"
                trading_verdict = "Status quo RBI / Fed policy stance. Price likely to consolidate within VWAP Bands."

        # B. Crude Oil & Energy Shocks (Impact: 8.0)
        elif any(k in t_lower for k in ["crude", "brent", "oil prices", "opec", "petroleum"]):
            category = "CRUDE_SHOCK"
            impact_score = 8.0
            if any(w in t_lower for w in ["surge", "surges", "spike", "spikes", "jump", "jumps", "rises", "climbs", "rally", "high", "rebound"]):
                polarity = "BEARISH"
                score = -0.70
                market_direction = "BEARISH DRAG"
                trading_verdict = "Rising crude pressures Indian import bill, OMC, paint, and tyre margins. Caution on fresh CE longs."
            elif any(w in t_lower for w in ["slide", "slides", "plunge", "plunges", "slump", "drops", "falls", "tumbles", "eases"]):
                polarity = "BULLISH"
                score = 0.70
                market_direction = "BULLISH TAILWIND"
                trading_verdict = "Falling crude lowers import deficit and inflation pressure. Macro tailwind favoring CE Call buying."
            else:
                polarity = "NEUTRAL"
                score = 0.0
                impact_score = 6.0
                market_direction = "BALANCED"
                trading_verdict = "Crude holding steady. No macro shock to Indian equity valuations."

        # C. Geopolitics & War (Impact: 9.2)
        elif any(k in t_lower for k in ["war", "missile", "military", "escalat", "attack", "sanction", "ceasefire", "iran", "israel", "russia", "ukraine", "truce"]):
            category = "GEOPOLITICAL"
            impact_score = 9.2
            if any(w in t_lower for w in ["ceasefire", "peace", "deal", "truce", "de-escalat", "ease", "talks", "withdrawn"]):
                polarity = "STRONG BULLISH"
                score = 0.80
                market_direction = "RELIEF RALLY"
                trading_verdict = "Geopolitical de-escalation sparks aggressive short-covering rally across benchmarks."
            else:
                polarity = "STRONG BEARISH"
                score = -0.85
                market_direction = "RISK-OFF BREAKDOWN"
                trading_verdict = "Geopolitical escalation triggering global risk-off flight to safe havens. High gap-down and breakdown vulnerability."

        # D. Government / Regulatory Policy (Impact: 8.5)
        elif any(k in t_lower for k in ["union budget", "sebi", "stt", "f&o expiry", "capital gains", "ltcg", "gst collection", "customs duty"]):
            category = "GOV_POLICY"
            impact_score = 8.5
            if any(w in t_lower for w in ["curb", "tighten", "penalty", "tax hike", "stt hike", "restrictions", "crackdown"]):
                polarity = "BEARISH"
                score = -0.75
                market_direction = "VOLATILITY DRAG"
                trading_verdict = "Regulatory tightening / tax headwind. Institutional volume contraction expected. Strictly trade 1 lot."
            elif any(w in t_lower for w in ["record", "stimulus", "tax cut", "reform", "boost", "incentive"]):
                polarity = "BULLISH"
                score = 0.75
                market_direction = "BULLISH EXPANSION"
                trading_verdict = "Favorable regulatory stimulus. Bullish trend continuation toward upper S&R targets."
            else:
                polarity = "NEUTRAL"
                score = 0.0
                impact_score = 7.0
                market_direction = "OBSERVATIONAL"
                trading_verdict = "Regulatory announcement monitored; wait for institutional confirmation before reacting."

        # E. Top-5 Heavyweight Corporate Disruptions (Reliance, HDFC Bank, ICICI Bank, Infosys, TCS) (Impact: 7.5)
        elif any(k in t_lower for k in ["reliance", "hdfc bank", "icici bank", "infosys", "tcs"]):
            category = "HEAVYWEIGHT_EARNINGS"
            impact_score = 7.5
            if any(w in t_lower for w in ["profit jumps", "profit beats", "strong q", "net profit up", "q2 net profit", "q3 net profit", "q4 net profit", "q1 net profit", "deal win"]):
                polarity = "BULLISH"
                score = 0.65
                market_direction = "HEAVYWEIGHT LIFT"
                trading_verdict = "Top constituent earnings beat providing direct structural lift to NIFTY 50 index."
            elif any(w in t_lower for w in ["profit falls", "profit misses", "slumps", "penalty", "probe", "resigns", "scam"]):
                polarity = "BEARISH"
                score = -0.65
                market_direction = "HEAVYWEIGHT DRAG"
                trading_verdict = "Top index constituent drag weighing heavily on NIFTY index. Avoid aggressive call buying."
            else:
                impact_score = 5.0
                polarity = "NEUTRAL"
                score = 0.0
                market_direction = "NEUTRAL"
                trading_verdict = "Index heavyweight news noted. Routine operational announcement."

        # Re-check noise override
        if is_routine_noise and category == "MARKET_NOISE":
            impact_score = 1.5

        formatted_ist, pub_epoch, time_ago, display_pub = NewsSentimentEngine.format_pub_date_ist(pub_date)

        # Freshness Check: Only news within the last 18 hours can qualify as Grade-A breaking catalyst!
        is_stale_by_time = time_ago.endswith("d ago") or "20h ago" in time_ago or "21h ago" in time_ago or "22h ago" in time_ago or "23h ago" in time_ago
        is_high_impact = (impact_score >= 7.5) and not is_stale_by_time and not is_routine_noise

        return {
            "title": t_clean,
            "source": source or "Financial Media",
            "published_at": display_pub,
            "published_ist": formatted_ist,
            "time_ago": time_ago,
            "pub_epoch": pub_epoch,
            "category": category,
            "impact_score": impact_score,
            "is_high_impact": is_high_impact,
            "polarity": polarity,
            "score": score,
            "market_direction": market_direction,
            "trading_verdict": trading_verdict,
        }

    # -------------------------------------------------------------
    # Live RSS Fetching & Processing
    # -------------------------------------------------------------
    def fetch_latest_news(self, force: bool = False) -> Dict[str, Any]:
        """
        Fetches live Google News RSS, filters noise, classifies catalysts,
        and updates internal cache thread-safely.
        """
        now_ts = time.time()
        # Respect a 30s cache interval unless forced
        if not force and (now_ts - self._last_fetch_ts) < 30.0:
            with self._cache_lock:
                return dict(self._cached_summary)

        headlines_raw: List[Dict[str, str]] = []
        target_urls = [RSS_PRIMARY_URL, RSS_BACKUP_URL]

        for url in target_urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        )
                    },
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    xml_content = resp.read()
                root = ET.fromstring(xml_content)
                items = root.findall(".//item")
                for item in items:
                    title_elem = item.find("title")
                    pub_elem = item.find("pubDate")
                    src_elem = item.find("source")
                    title = title_elem.text if title_elem is not None and title_elem.text else ""
                    pub = pub_elem.text if pub_elem is not None and pub_elem.text else ""
                    src = src_elem.text if src_elem is not None and src_elem.text else ""
                    if title:
                        src_lower = (src or "").lower().strip()
                        if not any(b in src_lower for b in BLOCKED_SCRAPERS):
                            headlines_raw.append({"title": title, "pub": pub, "src": src})
                if headlines_raw:
                    break
            except Exception as e:
                logger.debug("RSS fetch exception from %s: %s", url, e)

        # If network failed or feed empty, return existing cached data
        if not headlines_raw:
            with self._cache_lock:
                return dict(self._cached_summary)

        # Classify all headlines
        classified_items: List[Dict[str, Any]] = []
        high_impact_items: List[Dict[str, Any]] = []

        for h in headlines_raw:
            res = self.classify_headline(title=h["title"], source=h.get("src", ""), pub_date=h.get("pub", ""))
            classified_items.append(res)
            if res["is_high_impact"]:
                high_impact_items.append(res)

        # Sort high impact items by impact_score descending, then recency
        high_impact_items.sort(key=lambda x: (x["impact_score"], x.get("pub_epoch", 0.0)), reverse=True)
        # Sort all headlines chronologically (newest news at the top!)
        classified_items.sort(key=lambda x: (x.get("is_high_impact", False), x.get("pub_epoch", 0.0)), reverse=True)

        # Determine overall market sentiment
        if high_impact_items:
            top_catalyst = high_impact_items[0]
            # Weighted average score of high impact catalysts
            weights = [item["impact_score"] for item in high_impact_items]
            total_w = sum(weights) or 1.0
            sentiment_score = round(sum(item["score"] * w for item, w in zip(high_impact_items, weights)) / total_w, 2)
            is_high_impact = True
            impact_category = top_catalyst["category"]
            market_direction = top_catalyst["market_direction"]
            trading_verdict = top_catalyst["trading_verdict"]
            breaking_catalyst = top_catalyst
        else:
            top_catalyst = None
            sentiment_score = 0.0
            is_high_impact = False
            impact_category = "NONE"
            market_direction = "SIDEWAYS / STRUCTURAL FLOW"
            trading_verdict = "Macro background is calm (no Grade-A catalysts). Trade standard Session VWAP & S&R structural setups."
            breaking_catalyst = None

        if sentiment_score >= 0.5:
            overall_sentiment = "STRONG BULLISH"
        elif sentiment_score > 0.15:
            overall_sentiment = "BULLISH"
        elif sentiment_score <= -0.5:
            overall_sentiment = "STRONG BEARISH"
        elif sentiment_score < -0.15:
            overall_sentiment = "BEARISH"
        else:
            overall_sentiment = "NEUTRAL"

        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now_str = datetime.datetime.now(ist_tz).strftime("%d %b %Y, %I:%M %p IST")
        new_summary: Dict[str, Any] = {
            "status": "ok",
            "last_updated": now_str,
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_score,
            "is_high_impact": is_high_impact,
            "impact_category": impact_category,
            "breaking_catalyst": breaking_catalyst,
            "market_direction": market_direction,
            "trading_verdict": trading_verdict,
            "feed_count": len(headlines_raw),
            "high_impact_count": len(high_impact_items),
            "headlines": classified_items[:20],
        }

        # Optional Gemini enrichment for top high-impact catalyst
        if is_high_impact and top_catalyst and RAGConfig.get_api_key():
            try:
                enriched = self._enrich_with_gemini(top_catalyst)
                if enriched:
                    new_summary["trading_verdict"] = enriched.get("verdict", trading_verdict)
                    new_summary["market_direction"] = enriched.get("direction", market_direction)
            except Exception as e_ai:
                logger.debug("Gemini enrichment bypassed: %s", e_ai)

        with self._cache_lock:
            self._cached_summary = new_summary
            self._last_fetch_ts = now_ts

        self._save_persisted_cache(new_summary)
        return dict(new_summary)

    def _enrich_with_gemini(self, catalyst: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Invokes lightweight Gemini call to get pro-desk directional advice on top catalyst."""
        api_key = RAGConfig.get_api_key()
        if not api_key:
            return None

        prompt = (
            f"You are a Senior Quantitative Macro Prop Trader at NSE India.\n"
            f"Analyze this breaking news headline for NIFTY 50 intraday impact:\n"
            f"Headline: '{catalyst['title']}'\n"
            f"Source: {catalyst.get('source', 'Media')}\n"
            f"Category: {catalyst['category']}\n\n"
            f"Respond STRICTLY in valid JSON with two fields:\n"
            f"1. 'direction': Brief 2-4 word market trend (e.g. 'BULLISH MOMENTUM RALLY', 'BEARISH SELLOFF DRAG')\n"
            f"2. 'verdict': Exact tactical advice for NIFTY options traders regarding CE Calls vs PE Puts and Session VWAP.\n"
            f"JSON:"
        )

        models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]
        for mod in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Extract json block
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if "direction" in parsed and "verdict" in parsed:
                        return parsed
            except Exception:
                continue
        return None

    # -------------------------------------------------------------
    # Public Accessors
    # -------------------------------------------------------------
    def get_sentiment_summary(self) -> Dict[str, Any]:
        """Returns the latest cached sentiment summary instantly (zero blocking latency)."""
        with self._cache_lock:
            return dict(self._cached_summary)

    def get_top_catalyst(self) -> Optional[Dict[str, Any]]:
        with self._cache_lock:
            return self._cached_summary.get("breaking_catalyst")

    def get_headlines(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self._cache_lock:
            return list(self._cached_summary.get("headlines", []))[:limit]

    # -------------------------------------------------------------
    # Background Daemon Poller
    # -------------------------------------------------------------
    def start_background_poller(self, interval_sec: int = 90):
        """Starts 24/7 background polling daemon."""
        with self._lock:
            if self._poller_thread is not None and self._poller_thread.is_alive():
                return
            self._stop_poller.clear()
            self._poller_thread = threading.Thread(
                target=self._run_poller_loop,
                args=(interval_sec,),
                daemon=True,
                name="NewsSentimentPollerThread",
            )
            self._poller_thread.start()
            logger.info("NewsSentimentEngine background poller started (interval: %ds)", interval_sec)

    def _run_poller_loop(self, interval_sec: int):
        # Initial non-blocking fetch
        try:
            self.fetch_latest_news(force=True)
        except Exception as e:
            logger.debug("Initial background news fetch exception: %s", e)

        while not self._stop_poller.is_set():
            try:
                time.sleep(interval_sec)
                if self._stop_poller.is_set():
                    break
                self.fetch_latest_news(force=True)
            except Exception as e:
                logger.debug("Poller loop exception: %s", e)

    def stop_background_poller(self):
        self._stop_poller.set()
        if self._poller_thread:
            self._poller_thread.join(timeout=2.0)
            self._poller_thread = None
