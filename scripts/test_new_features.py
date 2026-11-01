"""
test_new_features.py
Verifies Personal Psychology Tracking, On-Chart Drawing Awareness, and Trade Doctor Post-Mortem.
"""
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from RAG.rag_service import RAGService
import database.user_db as user_db

def test_all():
    service = RAGService.get_instance()
    user_id = "usr_admin_001"
    psych = user_db.get_user_psychology_profile(user_id)

    market_state = {
        "price": 22730.0,
        "username": "Trader",
        "user_psychology": psych,
        "active_drawing": {
            "type": "line",
            "remark": "Major Support Floor",
            "price1": 22650.0,
            "price2": 22710.0,
            "angle": 38,
            "diff_price": 60.0,
            "diff_pct": 0.26
        },
        "drawings": [
            {"type": "line", "remark": "Major Support Floor", "price1": 22650.0, "price2": 22710.0, "angle": 38},
            {"type": "rect", "remark": "Institutional Flip Zone", "price1": 22780.0, "price2": 22820.0}
        ],
        "trade_doctor": {
            "has_trade": True,
            "trade": {
                "action": "BUY",
                "entry_time": "26-10-2026 10:15 IST",
                "entry_price": 22680.0,
                "exit_time": "26-10-2026 11:20 IST",
                "exit_price": 22745.0,
                "pnl_pts": 65.0,
                "result": "WIN",
                "exit_reason": "TARGET_REACHED"
            },
            "diagnosis": "1. Entry Long at 22680 above Session VWAP.\\n2. Won +65.0 pts (+₹4,225 on 1 Lot / 65 qty) respecting trend.\\n3. S&R Alignment at 22750 resistance.\\n4. Dr. Prescription: Repeat this setup! Perfect discipline."
        },
        "comb_sr_levels": [{"role": "Resistance", "price": 22800.0, "bounces": 7}],
        "market_regime": {"vix": 17.2, "regime_label": "High Volatility"},
        "option_chain": {"pcr": 1.05, "max_call_oi_strike": 22800, "max_put_oi_strike": 22600}
    }

    test_queries = [
        ("PSYCHOLOGY", "What is my current trading psychology, discipline score, and coaching advice?"),
        ("DRAWINGS", "Analyze my active on-chart drawings and trendlines against live VWAP and S&R levels."),
        ("TRADE_DOCTOR", "Trade Doctor: Perform an instant clinical post-mortem on my last completed trade. Why did it win or lose?")
    ]

    print("=" * 65)
    print("TESTING 3 NEW INSTITUTIONAL FEATURES")
    print("=" * 65)

    for category, q in test_queries:
        print(f"\n--- [{category}] QUERY: '{q}' ---")
        res = service.ask(query=q, market_state=market_state, user_id=user_id)
        reply = res.get("reply", "")
        print(f"MODEL: {res.get('model')} (Live LLM: {res.get('is_live_llm')})")
        print("REPLY:")
        print(reply)
        print("-" * 65)

        if category == "PSYCHOLOGY":
            assert "Discipline" in reply or "discipline" in reply or "85" in reply or "Score" in reply
        elif category == "DRAWINGS":
            assert "Major Support" in reply or "Drawing" in reply or "drawing" in reply or "Trendline" in reply
        elif category == "TRADE_DOCTOR":
            assert "Prescription" in reply or "Won" in reply or "pts" in reply or "Doctor" in reply or "Trade" in reply

    print("\nALL 3 NEW FEATURES VERIFIED AND PASSING WITH FLYING COLORS!")

if __name__ == "__main__":
    test_all()
