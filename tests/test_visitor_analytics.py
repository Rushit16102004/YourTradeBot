"""
tests/test_visitor_analytics.py
Unit tests for Real-Time Visitor Analytics, Online Tracking, and 1-Click CSV Download.
"""
import pytest
from datetime import datetime
import database.user_db as user_db


class TestVisitorAnalytics:
    def test_01_init_and_record_visitor_hit(self):
        user_db.init_database()
        test_vid = f"vis_unit_test_{int(datetime.utcnow().timestamp())}"
        
        # 1. Record hit as guest
        res = user_db.record_visitor_hit(
            visitor_id=test_vid,
            ip="192.168.1.100",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            path="/",
            referrer="https://google.com"
        )
        assert res["status"] == "ok"
        assert res["device_type"] == "Mobile"

        # 2. Verify summary reflects the guest hit
        summary = user_db.get_visitor_analytics_summary()
        assert summary["status"] == "ok"
        assert summary["total_unique_visitors"] >= 1
        assert summary["active_online"] >= 1
        assert "device_breakdown" in summary

    def test_02_heartbeat_pulse(self):
        test_vid = f"vis_unit_test_{int(datetime.utcnow().timestamp())}"
        user_db.record_visitor_hit(visitor_id=test_vid)
        
        # Pulse heartbeat
        active = user_db.record_visitor_heartbeat(visitor_id=test_vid)
        assert active >= 1

    def test_03_link_visitor_to_account(self):
        test_vid = f"vis_unit_test_{int(datetime.utcnow().timestamp())}"
        user_db.record_visitor_hit(visitor_id=test_vid)
        
        # Link to admin user
        ok = user_db.link_visitor_to_account(visitor_id=test_vid, user_id="usr_admin_001")
        assert ok is True

        summary = user_db.get_visitor_analytics_summary()
        assert summary["registered_visitors"] >= 1

    def test_04_csv_generation(self):
        csv_path = user_db.sync_users_to_csv()
        assert csv_path != ""
        import os
        assert os.path.exists(csv_path)
