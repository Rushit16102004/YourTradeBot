"""
RAG/news_sentiment_engine.py
Real-Time High-Impact News Sentiment & Macro Catalyst Engine with Session Memory.

Session Rules (NSE Indian Market Cycle):
1. 24H Working Trading Day Memory:
   - News accumulates from 4:00 PM of the previous working trading day until 4:00 PM of the current day.
   - Every working trading day at 4:00 PM IST (market post-close), the old news storage is emptied,
     and a new accumulation cycle starts for the next trading day.
2. Weekend & Holiday Hold (72H+ Accumulation):
   - For Monday trading, news accumulates from Friday 4:00 PM to Monday 4:00 PM (72 hours).
   - On Saturday, Sunday, or declared exchange holidays, news is NEVER wiped at 4:00 PM;
     it is held and accumulated until 4:00 PM of the next working trading day.
3. Market Behavior & Polarity Decision:
   - Evaluated dynamically using ALL news currently held in session temp memory.
   - High-impact Grade-A catalysts (RBI repo rate, Crude oil price surge/slump, War/Geopolitics, SEBI F&O curbs)
     provide directional conviction (CE Calls vs PE Puts).
   - In calm periods, aggregate session sentiment provides macro tailwind/headwind context.
4. Strict Filtering:
   - Retains ONLY news relevant to Indian stock market, NIFTY 50, Sensex, Crude Oil, and Macro Drivers.
   - Filters out non-market trivia (Warren Buffett diet, car launches, Bollywood) and scrapers (Bankersadda, FXStreet, etc.).
"""

from __future__ import annotations

import datetime
import email.utils
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

# Indian Standard Time Zone
IST_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# NSE Exchange Holidays for 2026/2027
NSE_HOLIDAYS_2026 = {
    datetime.date(2026, 1, 26),  # Republic Day
    datetime.date(2026, 3, 3),   # Holi
    datetime.date(2026, 3, 20),  # Id-Ul-Fitr
    datetime.date(2026, 4, 3),   # Good Friday
    datetime.date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    datetime.date(2026, 5, 1),   # Maharashtra Day
    datetime.date(2026, 5, 27),  # Bakri Id / Eid-Ul-Adha
    datetime.date(2026, 6, 26),  # Muharram
    datetime.date(2026, 8, 15),  # Independence Day
    datetime.date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    datetime.date(2026, 10, 20), # Dussehra
    datetime.date(2026, 11, 8),  # Diwali Laxmi Pujan
    datetime.date(2026, 11, 24), # Gurunanak Jayanti
    datetime.date(2026, 12, 25), # Christmas
}


def is_trading_day(d: datetime.date) -> bool:
    """Returns True if the given date is a working NSE trading day (Mon-Fri and not an exchange holiday)."""
    return d.weekday() < 5 and d not in NSE_HOLIDAYS_2026


def get_session_start_ist(now_ist: datetime.datetime) -> datetime.datetime:
    """
    Computes the start timestamp of the current trading news session:
    - On a working trading day at/after 4:00 PM IST: Session starts today at 4:00 PM IST.
    - Before 4:00 PM IST, or on weekends / exchange holidays:
      Rolls back to the previous working trading day at 4:00 PM IST.
    Examples:
    - Monday 08:53 AM -> Friday 4:00 PM (72h weekend accumulation)
    - Tuesday 10:00 AM -> Monday 4:00 PM (24h weekday accumulation)
    - Tuesday 04:05 PM -> Tuesday 4:00 PM (reset for Wednesday)
    """
    today = now_ist.date()
    today_4pm = datetime.datetime.combine(today, datetime.time(16, 0), tzinfo=now_ist.tzinfo)

    if is_trading_day(today) and now_ist >= today_4pm:
        return today_4pm

    check_date = today - datetime.timedelta(days=1)
    while not is_trading_day(check_date):
        check_date -= datetime.timedelta(days=1)

    return datetime.datetime.combine(check_date, datetime.time(16, 0), tzinfo=now_ist.tzinfo)


BLOCKED_SCRAPERS = [
    "dd news", "kucoin", "scanx", "bbn times", "pragativadi", "investment guru", "cryptocurrency",
    "motor octane", "motoroctane", "rushlane", "gaadiwaadi", "autocar", "carwale", "zigwheels",
    "bankersadda", "studycafe", "adda247", "testbook", "shiksha", "jagranjosh", "sarkari",
    "energynow", "beinsure", "fxstreet"
]

STALE_ANACHRONISMS = [
    r"fed rate hike", r"midterm election", r"crude oil above \$11", r"nse ipo in focus",
    r"nse ipo listed", r"listing today"
]

NOISE_PATTERNS = [
    r"chartist talk", r"what history suggest", r"what 25 yrs", r"stocks to buy",
    r"brokerage recommends", r"target price", r"stock picks", r"portfolio advice",
    r"mutual fund inflow", r"top gainers", r"top losers", r"buzzing stocks",
    r"technical view", r"what to expect", r"hot stocks", r"penny stocks",
    r"hasn't had water", r"drinks instead", r"revealed ahead", r"\bvs\b",
    r"should you pay", r"supersonic jet", r"first look", r"mileage",
    r"spotted flying", r"age of the imperial ceo", r"horoscope", r"movie",
    r"celebrity", r"actor", r"actress", r"box office"
]

CACHE_FILE = Path(__file__).resolve().parent.parent / "temp_storage" / "news_sentiment_cache.json"
SESSION_STORE_FILE = Path(__file__).resolve().parent.parent / "temp_storage" / "news_session_store.json"


def is_indian_market_relevant(title: str) -> bool:
    """Verifies that the headline directly concerns Indian financial markets, commodities, or key macro drivers."""
    t = title.lower()
    indian_market_patterns = [
        r"\bnifty\b", r"\bsensex\b", r"\bsebi\b", r"\brbi\b", r"\bd-street\b",
        r"\bdalal street\b", r"\bstock markets?\b", r"\bindian markets?\b",
        r"\bequities\b", r"\bindian equity\b", r"\bcrude oil\b", r"\bbrent\b",
        r"\breliance\b", r"\bhdfc\b", r"\bicici\b", r"\btcs\b", r"\binfosys\b",
        r"\bsbi\b", r"\bgst collection\b", r"\brepo rate\b", r"\bmonetary policy\b",
        r"\binflation\b", r"\bf&o\b", r"\bbank nifty\b", r"\bfii\b", r"\bdii\b",
        r"\bshaktikanta\b", r"\bfederal reserve\b", r"\bfomc\b", r"\bwar\b", r"\bmissiles?\b",
        r"\bceasefire\b", r"\bmilitary\b", r"\bgift nifty\b"
    ]
    return any(re.search(p, t) for p in indian_market_patterns)


def is_analyst_or_preview(title: str) -> bool:
    """Detects routine commentary, weekly outlooks, or analyst opinions that should not trigger market shock alerts."""
    t = title.lower()
    preview_patterns = [
        r"\banalysts?\b", r"\bview\b", r"\bviews\b", r"\bexpectations?\b",
        r"\bahead of market\b", r"\bthings to watch\b", r"\bfactors to watch\b",
        r"\bsteer markets?\b", r"\bweek ahead\b", r"\bwhat history suggests\b",
        r"\bwhat to expect\b", r"\bfrom wall street to d-street\b",
        r"\bstocks? to watch\b", r"\bstock picks?\b", r"\bchartist\b",
        r"\bwhat 25 yrs\b", r"\btarget price\b", r"\bbrokerage\b",
        r"\blikely to remain\b", r"\bfaces another\b", r"\bwill decide\b",
        r"\bweekly column\b", r"\bcolumn\b", r"\breport\b", r"\bpotential\b",
        r"\bforecast\b", r"\bpredict\b", r"\bmay ease\b", r"\bby march\b",
        r"\bspeculat\w*\b", r"\bfears?\b"
    ]
    return any(re.search(p, t) for p in preview_patterns)


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
        now_ist = datetime.datetime.now(IST_TZ)
        session_start = get_session_start_ist(now_ist)
        return {
            "status": "ok",
            "last_updated": now_ist.strftime("%d %b %Y, %I:%M %p IST"),
            "session_start_ist": session_start.strftime("%d %b %Y, %I:%M %p IST"),
            "session_hours": round((now_ist - session_start).total_seconds() / 3600.0, 1),
            "overall_sentiment": "NEUTRAL",
            "sentiment_score": 0.0,
            "is_high_impact": False,
            "impact_category": "NONE",
            "breaking_catalyst": None,
            "market_direction": "SIDEWAYS / STRUCTURAL FLOW",
            "trading_verdict": f"Macro background is calm in current session (since {session_start.strftime('%d %b, %I:%M %p')}). Follow Session VWAP and S&R boundaries.",
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
    # Session Temp Storage Management (Empty at 4pm on Trading Days)
    # -------------------------------------------------------------
    def _load_session_store(self, current_session_start: datetime.datetime) -> Dict[str, Any]:
        """
        Loads the session news store from temp_storage/news_session_store.json.
        If current_session_start > stored session_start (meaning a trading day 4:00 PM has passed),
        it EMPTIES all old news storage and starts a fresh session!
        """
        curr_epoch = current_session_start.timestamp()
        try:
            if SESSION_STORE_FILE.exists():
                data = json.loads(SESSION_STORE_FILE.read_text(encoding="utf-8"))
                stored_epoch = data.get("session_start_epoch", 0.0)
                if stored_epoch == curr_epoch and "articles" in data and isinstance(data["articles"], dict):
                    return data["articles"]
                else:
                    logger.info(
                        "4:00 PM Session Reset triggered! Cleared old news store (Stored: %s, Current: %s)",
                        data.get("session_start_ist", "Unknown"),
                        current_session_start.strftime("%d %b %Y, %I:%M %p IST"),
                    )
        except Exception as e:
            logger.debug("Session store load exception: %s", e)

        return {}

    def _save_session_store(self, current_session_start: datetime.datetime, articles: Dict[str, Any]):
        """Persists accumulated session news into temp_storage/news_session_store.json."""
        try:
            SESSION_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "session_start_epoch": current_session_start.timestamp(),
                "session_start_ist": current_session_start.strftime("%d %b %Y, %I:%M %p IST"),
                "last_updated_ist": datetime.datetime.now(IST_TZ).strftime("%d %b %Y, %I:%M %p IST"),
                "article_count": len(articles),
                "articles": articles,
            }
            SESSION_STORE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.debug("Session store save exception: %s", e)

    # -------------------------------------------------------------
    # Noise Filtering & Heuristic Classification
    # -------------------------------------------------------------
    @staticmethod
    def format_pub_date_ist(pub_date_str: str) -> tuple[str, float, str, str]:
        """
        Converts any international GMT / UTC / RFC-2822 date to Indian Standard Time (IST).
        Returns: (formatted_ist, epoch_seconds, time_ago, full_display_str)
        """
        if not pub_date_str:
            return "Recently", 0.0, "Recently", "Recently"
        try:
            dt_utc = email.utils.parsedate_to_datetime(pub_date_str)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
            dt_ist = dt_utc.astimezone(IST_TZ)
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
    def classify_headline(title: str, source: str = "", pub_date: str = "", link: str = "") -> Dict[str, Any]:
        """
        Classifies individual headline into high-impact macro categories vs routine noise,
        assigning impact score (1 to 10), polarity (-1.0 to 1.0), and directional trade bias.
        """
        t_clean = title.strip()
        t_lower = t_clean.lower()

        # 0. Reject non-Indian market news, low-tier scrapers, and stale recycled articles
        s_lower = source.lower().strip()
        is_blocked_source = any(b in s_lower for b in BLOCKED_SCRAPERS)
        is_stale_article = any(re.search(p, t_lower) for p in STALE_ANACHRONISMS)
        is_relevant_market = is_indian_market_relevant(t_clean)
        is_preview = is_analyst_or_preview(t_clean)
        is_routine_noise = any(re.search(p, t_lower) for p in NOISE_PATTERNS)

        if is_blocked_source or is_stale_article or not is_relevant_market:
            category = "MARKET_NOISE"
            impact_score = 1.0
            return {
                "title": t_clean,
                "source": source or "Financial Media",
                "link": link or "",
                "published_at": "Stale / Non-Market News",
                "published_ist": "Filtered",
                "time_ago": "Filtered",
                "pub_epoch": 0.0,
                "category": "MARKET_NOISE",
                "impact_score": 1.0,
                "is_high_impact": False,
                "polarity": "NEUTRAL",
                "score": 0.0,
                "market_direction": "SIDEWAYS",
                "trading_verdict": "Non-market related or recycled news filtered out.",
            }

        category = "MARKET_NOISE"
        impact_score = 2.0
        polarity = "NEUTRAL"
        score = 0.0
        market_direction = "SIDEWAYS"
        trading_verdict = "Routine market noise. Does not alter structural bias; rely on Session VWAP."

        # 2. High-Impact Category Classifications (Strictly require active catalyst conditions)

        # A. Central Bank / Monetary Policy (Impact: 9.0)
        cb_rate_trigger = (
            bool(re.search(r"\b(rbi|repo rate|monetary policy|mpc)\b", t_lower)) and
            any(w in t_lower for w in ["cut", "cuts", "slash", "slashes", "hike", "hikes", "raises", "rate decision", "repo rate by"])
        ) or (
            bool(re.search(r"\b(fed|fomc|federal reserve)\b", t_lower)) and
            any(w in t_lower for w in ["rate cut", "rate hike", "cuts rates", "raises rates", "slashes rates", "rate decision"])
        ) or (
            bool(re.search(r"\b(cpi inflation|retail inflation|wpi inflation)\b", t_lower)) and
            any(w in t_lower for w in ["spikes", "surges to", "jumps to", "cools to", "falls to", "eases to"])
        )

        is_admin_cb = any(w in t_lower for w in ["recruitment", "exam", "calendar", "jobs", "vacancy", "cyber", "advisory", "circular", "credit trend"])

        if cb_rate_trigger and not is_admin_cb and not is_preview:
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
        elif bool(re.search(r"\b(crude oil|brent crude|oil prices?)\b", t_lower)) and any(w in t_lower for w in ["surge", "surges", "spike", "spikes", "jump 3", "jump 4", "jump 5", "plunge", "plunges", "slump", "crashes", "tumbles", "slide"]) and not is_preview:
            category = "CRUDE_SHOCK"
            impact_score = 8.0
            if any(w in t_lower for w in ["surge", "surges", "spike", "spikes", "jump", "climbs"]):
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
        elif (
            bool(re.search(r"\b(airstrikes?|missile attack|missiles? strike|military invasion|military attack|war escalation|red sea attack)\b", t_lower)) and
            (bool(re.search(r"\b(iran|israel|russia|ukraine|middle east|gaza|red sea|hormuz|gulf)\b", t_lower)) or bool(re.search(r"\b(war|wars)\b", t_lower)))
        ) or bool(re.search(r"\b(ceasefire signed|peace deal signed|peace treaty|truce agreed|troops withdrawn)\b", t_lower)):
            category = "GEOPOLITICAL"
            impact_score = 9.2
            if any(w in t_lower for w in ["ceasefire", "peace agreement", "peace deal", "peace treaty", "truce signed", "de-escalat", "troops withdrawn", "truce agreed"]):
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
        elif bool(re.search(r"\b(union budget|sebi|stt hike|f&o ban|capital gains tax)\b", t_lower)):
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

        # E. Top-5 Heavyweight Corporate Disruptions (Impact: 7.5)
        elif bool(re.search(r"\b(reliance industries|hdfc bank|icici bank|infosys|tcs)\b", t_lower)) and any(w in t_lower for w in ["profit jumps", "profit beats", "net profit up 2", "q2 net profit jumps", "profit falls", "profit misses", "slumps"]):
            category = "HEAVYWEIGHT_EARNINGS"
            impact_score = 7.5
            if any(w in t_lower for w in ["profit jumps", "profit beats", "net profit up", "deal win"]):
                polarity = "BULLISH"
                score = 0.65
                market_direction = "HEAVYWEIGHT LIFT"
                trading_verdict = "Top constituent earnings beat providing direct structural lift to NIFTY 50 index."
            else:
                polarity = "BEARISH"
                score = -0.65
                market_direction = "HEAVYWEIGHT DRAG"
                trading_verdict = "Top index constituent drag weighing heavily on NIFTY index. Avoid aggressive call buying."

        # Noise & Analyst Preview override
        if is_routine_noise or is_preview:
            category = "MARKET_NOISE"
            impact_score = min(impact_score, 3.0)
            polarity = "NEUTRAL"
            score = 0.0
            market_direction = "SIDEWAYS"
            trading_verdict = "Routine analyst commentary; rely on technical Session VWAP."

        formatted_ist, pub_epoch, time_ago, display_pub = NewsSentimentEngine.format_pub_date_ist(pub_date)
        is_high_impact = (impact_score >= 7.5) and not is_routine_noise and not is_preview

        return {
            "title": t_clean,
            "source": source or "Financial Media",
            "link": link or "",
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
    # Live RSS Fetching & Session Accumulation
    # -------------------------------------------------------------
    def fetch_latest_news(self, force: bool = False) -> Dict[str, Any]:
        """
        Fetches live news, maintains persistent temp storage for the current session window
        (24H on weekdays, 72H on Mondays/weekends, multi-day on holidays), empties at 4:00 PM
        on every working trading day, and determines market behavior using all stored news.
        """
        now_ts = time.time()
        # Respect a 30s cache interval unless forced
        if not force and (now_ts - self._last_fetch_ts) < 30.0:
            with self._cache_lock:
                return dict(self._cached_summary)

        now_ist = datetime.datetime.now(IST_TZ)
        current_session_start = get_session_start_ist(now_ist)
        session_start_epoch = current_session_start.timestamp()
        hours_in_session = max(1.0, (now_ist - current_session_start).total_seconds() / 3600.0)

        # Load session news from temp storage (clears automatically if 4:00 PM on trading day has passed!)
        session_articles = self._load_session_store(current_session_start)

        # Dynamic query duration matching the active session length
        query_hours = max(24, min(120, int(hours_in_session) + 2))
        query_url = (
            f"https://news.google.com/rss/search?q=(NIFTY+OR+Sensex+OR+RBI+OR+SEBI+OR+\"stock+market\"+OR+\"crude+oil\")+when:{query_hours}h&hl=en-IN&gl=IN&ceid=IN:en"
        )
        backup_url = (
            f"https://news.google.com/rss/search?q=(NIFTY+OR+Sensex+OR+RBI+OR+SEBI+OR+\"Indian+economy\")+when:{query_hours}h&hl=en-IN&gl=IN&ceid=IN:en"
        )

        headlines_raw: List[Dict[str, str]] = []
        target_urls = [query_url, backup_url]

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
                with urllib.request.urlopen(req, timeout=8) as resp:
                    xml_content = resp.read()
                root = ET.fromstring(xml_content)
                items = root.findall(".//item")
                for item in items:
                    title_elem = item.find("title")
                    pub_elem = item.find("pubDate")
                    src_elem = item.find("source")
                    link_elem = item.find("link")
                    title = title_elem.text if title_elem is not None and title_elem.text else ""
                    pub = pub_elem.text if pub_elem is not None and pub_elem.text else ""
                    src = src_elem.text if src_elem is not None and src_elem.text else ""
                    link = link_elem.text if link_elem is not None and link_elem.text else ""
                    if title and pub:
                        src_lower = (src or "").lower().strip()
                        if not any(b in src_lower for b in BLOCKED_SCRAPERS):
                            headlines_raw.append({"title": title, "pub": pub, "src": src, "link": link})
                if headlines_raw:
                    break
            except Exception as e:
                logger.debug("RSS fetch exception from %s: %s", url, e)

        # Ingest new articles into session temp storage
        for h in headlines_raw:
            title_text = h["title"]
            pub_str = h["pub"]
            if not is_indian_market_relevant(title_text):
                continue
            if any(re.search(p, title_text.lower()) for p in NOISE_PATTERNS):
                continue
            if any(re.search(p, title_text.lower()) for p in STALE_ANACHRONISMS):
                continue

            try:
                dt_utc = email.utils.parsedate_to_datetime(pub_str)
                # Strictly discard anything published before the current session started!
                if dt_utc.timestamp() < session_start_epoch:
                    continue
            except Exception:
                continue

            res = self.classify_headline(title=title_text, source=h.get("src", ""), pub_date=pub_str, link=h.get("link", ""))
            if res.get("time_ago") != "Filtered":
                key = h.get("link") or title_text
                session_articles[key] = res

        # Persist updated session store
        self._save_session_store(current_session_start, session_articles)

        # Extract all stored session headlines
        all_session_items = list(session_articles.values())
        all_session_items.sort(key=lambda x: x.get("pub_epoch", 0.0), reverse=True)

        high_impact_items = [item for item in all_session_items if item.get("is_high_impact")]
        high_impact_items.sort(key=lambda x: (x.get("impact_score", 0.0), x.get("pub_epoch", 0.0)), reverse=True)

        # Determine market behavior according to ALL news in session temp storage
        session_start_disp = current_session_start.strftime("%d %b, %I:%M %p")
        if high_impact_items:
            top_catalyst = high_impact_items[0]
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
            is_high_impact = False
            impact_category = "NONE"
            breaking_catalyst = None

            # Calculate net aggregate sentiment from all accumulated headlines
            if all_session_items:
                avg_score = round(sum(item["score"] for item in all_session_items) / len(all_session_items), 2)
            else:
                avg_score = 0.0
            sentiment_score = avg_score

            if sentiment_score >= 0.25:
                market_direction = "BULLISH BIAS"
                trading_verdict = f"Net bullish sentiment across {len(all_session_items)} session headlines (since {session_start_disp}). Favor buying on VWAP retests."
            elif sentiment_score <= -0.25:
                market_direction = "BEARISH BIAS"
                trading_verdict = f"Net bearish sentiment across {len(all_session_items)} session headlines (since {session_start_disp}). Caution on fresh longs; watch VWAP breakdown levels."
            else:
                market_direction = "SIDEWAYS / STRUCTURAL FLOW"
                trading_verdict = f"Macro background is calm across {len(all_session_items)} session headlines (since {session_start_disp}). Trade standard Session VWAP & S&R structural setups."

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

        now_str = now_ist.strftime("%d %b %Y, %I:%M %p IST")
        new_summary: Dict[str, Any] = {
            "status": "ok",
            "last_updated": now_str,
            "session_start_ist": current_session_start.strftime("%d %b %Y, %I:%M %p IST"),
            "session_hours": round(hours_in_session, 1),
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_score,
            "is_high_impact": is_high_impact,
            "impact_category": impact_category,
            "breaking_catalyst": breaking_catalyst,
            "market_direction": market_direction,
            "trading_verdict": trading_verdict,
            "feed_count": len(all_session_items),
            "high_impact_count": len(high_impact_items),
            "headlines": all_session_items[:50],  # Display all accumulated session news (up to 50 items)
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

    def get_headlines(self, limit: int = 50) -> List[Dict[str, Any]]:
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
