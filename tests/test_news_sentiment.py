"""
tests/test_news_sentiment.py
Unit tests for Real-Time High-Impact News Sentiment & Macro Catalyst Engine.
Verifies:
1. Google News RSS classification accuracy (Grade-A catalysts vs routine market noise).
2. Proper polarity scoring (-1.0 to +1.0) and directional market guidance.
3. Strict noise filtering: Only Grade-A events (impact >= 7.5) trigger trade guidance.
4. Integration with Institutional Pre-Flight Check Engine.
"""

import pytest
from RAG.news_sentiment_engine import NewsSentimentEngine
from RAG.preflight import PreFlightEngine


class TestNewsSentimentEngine:
    def test_01_singleton_initialization(self):
        engine1 = NewsSentimentEngine.get_instance()
        engine2 = NewsSentimentEngine.get_instance()
        assert engine1 is engine2
        summary = engine1.get_sentiment_summary()
        assert isinstance(summary, dict)
        assert "overall_sentiment" in summary
        assert "sentiment_score" in summary
        assert "is_high_impact" in summary
        assert "trading_verdict" in summary

    def test_02_classify_central_bank_dovish_and_hawkish(self):
        # Dovish rate cut
        res_dovish = NewsSentimentEngine.classify_headline(
            "RBI unexpectedly cuts repo rate by 25 bps as inflation cools to 3.8%",
            source="Economic Times"
        )
        assert res_dovish["category"] == "CENTRAL_BANK"
        assert res_dovish["impact_score"] >= 8.5
        assert res_dovish["is_high_impact"] is True
        assert res_dovish["polarity"] == "STRONG BULLISH"
        assert res_dovish["score"] > 0.5
        assert "CE Call" in res_dovish["trading_verdict"]

        # Hawkish rate hike
        res_hawkish = NewsSentimentEngine.classify_headline(
            "US Fed raises rates by 50 bps amid persistent inflation shock",
            source="Reuters"
        )
        assert res_hawkish["category"] == "CENTRAL_BANK"
        assert res_hawkish["impact_score"] >= 8.5
        assert res_hawkish["is_high_impact"] is True
        assert res_hawkish["polarity"] == "STRONG BEARISH"
        assert res_hawkish["score"] < -0.5
        assert "PE Put" in res_hawkish["trading_verdict"]

    def test_03_classify_crude_oil_shock(self):
        # Crude surge -> Bearish for Indian economy
        res_surge = NewsSentimentEngine.classify_headline(
            "Crude oil prices surge 4.2% following Red Sea tanker disruption",
            source="Livemint"
        )
        assert res_surge["category"] == "CRUDE_SHOCK"
        assert res_surge["impact_score"] >= 7.5
        assert res_surge["is_high_impact"] is True
        assert res_surge["polarity"] == "BEARISH"
        assert res_surge["score"] < 0
        assert "Caution on fresh CE longs" in res_surge["trading_verdict"]

        # Crude slump -> Bullish for Indian economy
        res_fall = NewsSentimentEngine.classify_headline(
            "Brent crude prices plunge 3.8% as OPEC signals supply boost",
            source="CNBC"
        )
        assert res_fall["category"] == "CRUDE_SHOCK"
        assert res_fall["impact_score"] >= 7.5
        assert res_fall["polarity"] == "BULLISH"
        assert res_fall["score"] > 0

    def test_04_classify_geopolitical_conflict_and_ceasefire(self):
        # War escalation -> Strong Bearish
        res_war = NewsSentimentEngine.classify_headline(
            "Military missile attack reported near Gulf energy hub; war escalation feared",
            source="BBC"
        )
        assert res_war["category"] == "GEOPOLITICAL"
        assert res_war["impact_score"] >= 9.0
        assert res_war["is_high_impact"] is True
        assert res_war["polarity"] == "STRONG BEARISH"
        assert res_war["score"] <= -0.8

        # Ceasefire -> Strong Bullish relief
        res_peace = NewsSentimentEngine.classify_headline(
            "Historic ceasefire peace deal signed; regional conflict de-escalates",
            source="AP News"
        )
        assert res_peace["category"] == "GEOPOLITICAL"
        assert res_peace["impact_score"] >= 9.0
        assert res_peace["polarity"] == "STRONG BULLISH"
        assert res_peace["score"] >= 0.8

    def test_05_strict_noise_reduction(self):
        # Routine analyst chatter must be filtered out and NOT trigger high impact
        noise_headlines = [
            "Chartist Talk: Can confident bulls drive Nifty 50 beyond 23,500 next week?",
            "Top 5 stocks to buy today for 10% returns according to analysts",
            "Brokerage recommends buy on Tata Motors with target price of 1100",
            "What 25 yrs of market history suggest about November returns",
            "Daily mutual fund inflow reaches record levels in small cap category"
        ]
        for nh in noise_headlines:
            res = NewsSentimentEngine.classify_headline(nh, source="Analyst Blog")
            assert res["is_high_impact"] is False, f"Noise headline '{nh}' should NOT be high-impact!"
            assert res["impact_score"] < 7.5

    def test_06_preflight_integration(self):
        # Evaluate PreFlight and confirm news_sentiment is returned and evaluated
        res = PreFlightEngine.evaluate(direction="BUY", spot_price=24200.0)
        assert "news_sentiment" in res
        assert "overall_sentiment" in res["news_sentiment"]
        assert "sentiment_score" in res["news_sentiment"]
        assert "is_high_impact" in res["news_sentiment"]

        # Ensure checklist has item 7 Macro News Catalyst & Sentiment
        news_item = next((item for item in res["checklist"] if "Macro News" in item["name"]), None)
        assert news_item is not None
        assert news_item["status"] in ("PASS", "CAUTION", "FAIL")
        assert "badge" in news_item
        assert "detail" in news_item
    def test_07_anti_scraper_and_buffett_noise_rejection(self):
        # 1. Warren Buffett lifestyle trivia should NOT trigger war / geopolitical alert
        res_wb = NewsSentimentEngine.classify_headline(
            "Warren Buffett Hasn't Had Water In 48 Years, Here's What He Drinks Instead",
            source="NDTV",
            pub_date="Sat, 31 Oct 2026 16:25:00 GMT"
        )
        assert res_wb["category"] == "MARKET_NOISE"
        assert res_wb["is_high_impact"] is False
        assert res_wb["polarity"] == "NEUTRAL"

        # 2. Scrapers and auto blogs should be rejected
        res_dd = NewsSentimentEngine.classify_headline(
            "Stock markets trade marginally higher after US Fed rate hike; NSE IPO in focus",
            source="DD News"
        )
        assert res_dd["category"] == "MARKET_NOISE"
        assert res_dd["is_high_impact"] is False

        res_auto = NewsSentimentEngine.classify_headline(
            "Royal Enfield Himalayan 750 Revealed Ahead Of EICMA 2026 Debut",
            source="Gaadiwaadi.com"
        )
        assert res_auto["is_high_impact"] is False
