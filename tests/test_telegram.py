"""
Unit tests for Telegram Notifier without contact number.
"""
from datetime import datetime
import pytz
from telegram_notifier import TelegramNotifier

IST = pytz.timezone("Asia/Kolkata")


def test_telegram_unconfigured():
    notifier = TelegramNotifier(bot_token="", chat_id="", phone="")
    assert not notifier.is_configured
    ok, msg = notifier.send_message("Test")
    assert not ok
    assert "missing" in msg.lower()


def test_telegram_signal_formatting(monkeypatch):
    sent_payloads = []

    def mock_post(url, json=None, timeout=None):
        class MockResp:
            status_code = 200
            def json(self):
                return {"ok": True, "result": {"message_id": 123}}
        sent_payloads.append((url, json))
        return MockResp()

    monkeypatch.setattr("requests.post", mock_post)

    notifier = TelegramNotifier(bot_token="TEST_BOT_123", chat_id="TEST_CHAT_456")
    assert notifier.is_configured

    # 1. Startup Alert policy: Disabled per user requirement (only 3 core notification types active)
    ok, res = notifier.send_startup_alert()
    assert ok
    assert len(sent_payloads) == 0  # No startup alert dispatched

    # 2. BUY Signal
    sent_payloads.clear()
    ok, res = notifier.send_signal_alert(
        signal_name="BUY",
        price=22750.0,
        z_score=2.25,
        slope=0.0018,
        reason="ZFTF Entry",
        candle_time=datetime(2026, 10, 15, 14, 30, tzinfo=IST)
    )
    assert ok
    assert len(sent_payloads) == 1
    text = sent_payloads[0][1]["text"]
    assert "BUY / LONG ENTRY" in text
    assert "22,750.00" in text

    # 3. SELL Signal
    sent_payloads.clear()
    ok, res = notifier.send_signal_alert(
        signal_name="SELL",
        price=24120.0,
        pnl_pct=6.02,
        reason="TREND_EXIT",
        candle_time=datetime(2026, 10, 15, 14, 55, tzinfo=IST)
    )
    assert ok
    assert len(sent_payloads) == 1
    text_sell = sent_payloads[0][1]["text"]
    assert "SELL / EXIT POSITION" in text_sell

    # 4. EOD Alert (All positions exit today with date & time)
    sent_payloads.clear()
    ok, res = notifier.send_eod_alert(
        price=22730.0,
        in_position=True,
        entry_price=22600.0,
        pnl_pct=0.58,
        alert_time=datetime(2026, 10, 15, 15, 10, tzinfo=IST)
    )
    assert ok
    assert len(sent_payloads) == 1
    text_eod = sent_payloads[0][1]["text"]
    assert "ALL POSITIONS EXIT TODAY" in text_eod
    assert "Date:" in text_eod
    assert "Time:" in text_eod

    # 5. S&R Breakout Alert (CALL-CALL-CALL and PUT-PUT-PUT)
    sent_payloads.clear()
    ok_call, _ = notifier.send_sr_breakout_alert(
        signal_type="CALL",
        current_price=22510.0,
        broken_level_price=22480.0,
        broken_level_bounces=5,
        target_price=22560.0,
        target_gap=80.0,
    )
    assert ok_call
    assert len(sent_payloads) == 1
    call_text = sent_payloads[0][1]["text"]
    assert "CALL-CALL-CALL-CALL-CALL" in call_text
    assert "22,510.00" in call_text
    assert ">= 50 pts" in call_text

    sent_payloads.clear()
    ok_put, _ = notifier.send_sr_breakout_alert(
        signal_type="PUT",
        current_price=22380.0,
        broken_level_price=22400.0,
        broken_level_bounces=6,
        target_price=22320.0,
        target_gap=80.0,
    )
    assert ok_put
    assert len(sent_payloads) == 1
    put_text = sent_payloads[0][1]["text"]
    assert "PUT-PUT-PUT-PUT-PUT" in put_text
    assert "22,380.00" in put_text
    assert ">= 50 pts" in put_text
