import sys
import os
sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding='utf-8')
import logging
from RAG.rag_service import RAGService
from RAG.institutional_intelligence import (
    TimeOfDayRiskEngine,
    OptionChainIntelligence,
    MarketRegimeIntelligence,
    MicroTimeframeTriggerEngine,
    PositionSizingEngine,
)

logging.basicConfig(level=logging.ERROR)

def run_tests():
    print("=" * 60)
    print("RUNNING INSTITUTIONAL RAG PIPELINE VERIFICATION")
    print("=" * 60)

    # 1. Initialize RAG Service
    service = RAGService.get_instance()
    status = service.get_status()
    print("RAG Service Status:", status)
    assert status["stats"]["strategy_knowledge_count"] >= 18, f"Expected >= 18 strategy docs, got {status['stats']['strategy_knowledge_count']}"

    # 2. Build mock live market state
    spot_price = 22545.0
    tw = TimeOfDayRiskEngine.evaluate_window()
    oc = OptionChainIntelligence.analyze(spot_price)
    mr = MarketRegimeIntelligence.evaluate(13.8)
    mt = MicroTimeframeTriggerEngine.evaluate(None)
    ps = PositionSizingEngine.calculate(sl_points=20.0, capital=100000.0, risk_pct=1.5)

    market_state = {
        "username": "Rahul",
        "trading_style": "intraday_scalper",
        "price": spot_price,
        "time_window": tw,
        "option_chain": oc,
        "market_regime": mr,
        "micro_triggers": mt,
        "position_sizing": ps,
        "comb_sr_levels": [
            {"role": "Resistance", "price": 22620.0, "bounces": 7},
            {"role": "Support", "price": 22480.0, "bounces": 6},
        ],
        "technical_eval": {
            "vwap": {"value": 22510.0, "bias": "BULLISH", "upper_2": 22585.0, "lower_2": 22435.0, "dist_pts": 35.0},
            "ema": {"ema_9": 22530.0, "ema_20": 22515.0, "ema_50": 22490.0, "ema_200": 22420.0, "alignment": "BULLISH_STACK", "quality": "Strong Trend Momentum"},
            "oscillators": {"rsi_14": 56.5, "rsi_status": "Healthy Bullish", "macd_hist": 2.4, "macd_status": "Bullish"},
            "volume": {"current_volume": 42000, "volume_ma_20": 31000, "volume_ratio": 1.35, "status": "Above Average"},
            "reversal": {"risk_level": "LOW", "expected_reversal_analysis": "Trend healthy above Session VWAP."},
        },
        "last_signal": {"time": "26-10-2026 11:30 IST", "action": "BUY", "price": 22500.0, "reason": "BUY"},
        "last_entry_signal": {"time": "26-10-2026 11:30 IST", "action": "BUY", "price": 22500.0, "reason": "BUY"},
        "recent_signals": [{"time": "26-10-2026 11:30 IST", "action": "BUY", "price": 22500.0, "reason": "BUY"}],
    }

    test_queries = [
        ("Trade Entry Query", "When should I enter?"),
        ("Option Chain Query", "What is the PCR and option chain status?"),
        ("Time Window Query", "What is the current trading window?"),
        ("Position Sizing Query", "How many lots should I trade with 100k capital?"),
        ("Developer Contact", "Who developed this strategy?"),
        ("Confirmed Signal Query", "What is the current main signal?"),
    ]

    for title, q in test_queries:
        print(f"\n--- Testing: {title} ('{q}') ---")
        res = service.ask(query=q, market_state=market_state)
        reply = res.get("reply", "")
        print(f"Reply Length: {len(reply)} chars | Model: {res.get('model')}")
        print("Reply Snippet:\n", reply[:320] + "...\n")
        assert len(reply) > 40, f"Reply too short for query: {q}"
        assert "ZFTF" not in reply, f"Violation: Found 'ZFTF' in reply for query: {q}"

    print("=" * 60)
    print("ALL 6 INSTITUTIONAL RAG PIPELINE TESTS PASSED 100%!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
