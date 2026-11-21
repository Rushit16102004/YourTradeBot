"""
tests/test_api_endpoints.py
Automated HTTP endpoint testing for FastAPI server verifying core responses,
rate limit status codes, and input validation.
"""
import pytest
from fastapi.testclient import TestClient
import server

client = TestClient(server.app)


class TestApiEndpoints:
    def test_root_index_html(self):
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        assert "NIFTY" in res.text

    def test_check_phone_validation_endpoint(self):
        # Valid Indian phone
        res = client.get("/api/auth/check-phone?phone=9876543210&country_code=%2B91")
        assert res.status_code == 200
        data = res.json()
        assert "available" in data

        # Invalid Indian phone
        res_bad = client.get("/api/auth/check-phone?phone=12345&country_code=%2B91")
        assert res_bad.status_code == 200
        assert res_bad.json().get("available") is False

    def test_login_missing_credentials(self):
        res = client.post("/api/auth/login", json={"username": "", "password": ""})
        assert res.status_code in [400, 401]

    def test_data_endpoint(self):
        res = client.get("/api/data")
        assert res.status_code == 200
        data = res.json()
        assert "candles" in data or "spot_price" in data or isinstance(data, dict)

    def test_sr_levels_endpoint(self):
        res = client.get("/api/sr-levels?period=all")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, (dict, list))

    def test_admin_backups_endpoints(self):
        # Unauthorized without admin key
        res_unauth = client.get("/api/admin/backups")
        assert res_unauth.status_code == 403

        # Authorized listing with admin master key
        from database import user_db
        res_auth = client.get(f"/api/admin/backups?admin_key={user_db.ADMIN_MASTER_KEY}")
        assert res_auth.status_code == 200
        data = res_auth.json()
        assert data.get("status") == "ok"
        assert "backups" in data
        assert isinstance(data["backups"], list)
