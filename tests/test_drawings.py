"""
Tests for server-side drawing tools persistence API (/api/drawings).
"""
import json
import time
from fastapi.testclient import TestClient
from server import app, DRAWINGS_CACHE_FILE, _drawings_lock


def test_drawings_api_get_and_post(tmp_path):
    client = TestClient(app)

    sample_drawings = [
        {
            "id": "shape_12345",
            "type": "line",
            "time1": 1726900500,
            "price1": 25200.0,
            "time2": 1726904100,
            "price2": 25450.5,
            "color": "#2962ff",
            "width": 2,
            "remark": "Support Line"
        },
        {
            "id": "shape_67890",
            "type": "target_sl",
            "entry": 25300.0,
            "target": 25800.0,
            "stop": 25100.0,
            "timeStart": 1726900500,
            "timeEnd": 1726907700,
            "color": "#2962ff",
            "remark": "Trade Setup"
        }
    ]

    # POST new drawings
    resp_post = client.post("/api/drawings", json={"drawings": sample_drawings})
    assert resp_post.status_code == 200
    assert resp_post.json()["status"] == "ok"
    assert resp_post.json()["count"] == 2

    # GET drawings
    resp_get = client.get("/api/drawings")
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert "drawings" in data
    assert len(data["drawings"]) == 2
    assert data["drawings"][0]["id"] == "shape_12345"
    assert data["drawings"][0]["price1"] == 25200.0
    assert data["drawings"][1]["type"] == "target_sl"

    # Give async disk thread time to write
    time.sleep(0.3)
    assert DRAWINGS_CACHE_FILE.exists()
    with open(DRAWINGS_CACHE_FILE, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert len(disk_data) == 2
    assert disk_data[0]["id"] == "shape_12345"
