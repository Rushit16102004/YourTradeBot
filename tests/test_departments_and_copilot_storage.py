"""
tests/test_departments_and_copilot_storage.py
Comprehensive end-to-end test suite for:
1. Department Modularization (database, rag, indicators, temp_storage, broker, engine)
2. Copilot Query Storage in dedicated per-user tables (copilot_user_<username>)
3. Central Copilot Query Review Table (copilot_queries_review)
4. Admin Copilot Review API & User My-Queries API
5. Terminal Core APIs (Data, S&R, Indicators)
"""
import sys
import os
import json
import sqlite3
import urllib.request
import urllib.parse
from pathlib import Path

# Add project root to sys.path so tests can import all root & departmental packages
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"


def safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def make_request(path: str, method: str = "GET", data: dict = None, token: str = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            body = res.read().decode("utf-8")
            return res.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, json.loads(body) if body else {"error": str(e)}


def run_tests():
    safe_print("=" * 60)
    safe_print("STARTING TEST SUITE: DEPARTMENTS & PER-USER COPILOT STORAGE")
    safe_print("=" * 60)

    # 1. Admin Login
    safe_print("\n--- TEST 1: Admin Login ---")
    status, res = make_request("/api/auth/login", method="POST", data={
        "username": "admin",
        "password": "123@Qweasd"
    })
    assert status == 200, f"Admin login failed: {status} {res}"
    admin_token = res["token"]
    safe_print("Admin login successful. Token acquired.")

    # 2. Register/Login a New Test User
    safe_print("\n--- TEST 2: User Authentication & Profile ---")
    uname = "trader_rahul"
    email = "rahul@testterminal.com"
    pw = "RahulPass@2026"
    status, reg_res = make_request("/api/auth/register", method="POST", data={
        "username": uname,
        "email": email,
        "password": pw,
        "trading_style": "momentum_scalper",
        "accepted_policy": True
    })
    # If already registered, login
    if status != 200:
        status, login_res = make_request("/api/auth/login", method="POST", data={
            "username": uname,
            "password": pw
        })
        assert status == 200, f"Login failed: {login_res}"
        user_token = login_res["token"]
    else:
        user_token = reg_res["token"]
    safe_print(f"User '{uname}' logged in successfully.")

    # 3. User Asks a Question to AI Copilot
    safe_print("\n--- TEST 3: User Asks Question to Copilot (/api/rag/chat) ---")
    copilot_query = "What is the recommended trade setup given current VWAP slope and S&R zones?"
    status, chat_res = make_request("/api/rag/chat", method="POST", data={
        "message": copilot_query,
        "timeframe": "5m"
    }, token=user_token)
    assert status == 200, f"Copilot chat failed: {status} {chat_res}"
    preview = chat_res.get('reply', '')[:80].encode('ascii', 'replace').decode('ascii')
    safe_print(f"Copilot answered successfully. Reply preview: {preview}...")

    # 4. Verify Per-User Table and Review Table in SQLite Database
    safe_print("\n--- TEST 4: Verify Dedicated Table & Review Table in database/users.db ---")
    db_path = Path("database/users.db")
    assert db_path.exists(), "database/users.db not found!"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check dedicated user table exists: copilot_user_trader_rahul
    expected_table = f"copilot_user_{uname}"
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (expected_table,))
    tbl = cursor.fetchone()
    assert tbl is not None, f"Dedicated table {expected_table} was not created!"
    safe_print(f"PASS: Dedicated user table '{expected_table}' exists in database.")

    # Check query row inside user's dedicated table
    cursor.execute(f"SELECT * FROM {expected_table} ORDER BY id DESC LIMIT 1")
    user_row = cursor.fetchone()
    assert user_row is not None, f"No query records in {expected_table}"
    assert user_row["query"] == copilot_query
    safe_print(f"PASS: Query successfully logged into '{expected_table}'.")

    # Check query row inside central review table
    cursor.execute("SELECT * FROM copilot_queries_review WHERE username=? ORDER BY id DESC LIMIT 1", (uname,))
    review_row = cursor.fetchone()
    assert review_row is not None, "No review record found in copilot_queries_review!"
    assert review_row["review_status"] == "pending"
    review_id = review_row["id"]
    safe_print(f"PASS: Query logged in 'copilot_queries_review' with ID {review_id} (Status: pending).")
    conn.close()

    # 5. User Retrieves Own Queries (/api/copilot/my-queries)
    safe_print("\n--- TEST 5: User Retrieves Own History (/api/copilot/my-queries) ---")
    status, my_q_res = make_request("/api/copilot/my-queries", method="GET", token=user_token)
    assert status == 200, f"My queries failed: {my_q_res}"
    assert len(my_q_res.get("queries", [])) >= 1
    assert my_q_res["queries"][0]["query"] == copilot_query
    safe_print(f"PASS: User retrieved {len(my_q_res['queries'])} past queries from personal table.")

    # 6. Admin Reviews User Queries (/api/admin/copilot/queries)
    safe_print("\n--- TEST 6: Admin Queries Review Endpoint (/api/admin/copilot/queries) ---")
    status, admin_q_res = make_request("/api/admin/copilot/queries?status=pending", method="GET", token=admin_token)
    assert status == 200, f"Admin queries review failed: {admin_q_res}"
    assert admin_q_res["count"] >= 1
    assert expected_table in admin_q_res["user_tables"]
    safe_print(f"PASS: Admin retrieved {admin_q_res['count']} pending queries. User tables found: {admin_q_res['user_tables']}.")

    # 7. Admin Updates Query Review (/api/admin/copilot/review)
    safe_print("\n--- TEST 7: Admin Updates Query Review (/api/admin/copilot/review) ---")
    status, review_update_res = make_request("/api/admin/copilot/review", method="POST", data={
        "id": review_id,
        "status": "reviewed",
        "notes": "Verified SEBI-compliant response by Admin Lead."
    }, token=admin_token)
    assert status == 200 and review_update_res.get("success") is True, f"Review update failed: {review_update_res}"

    # Verify status changed to reviewed
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT review_status, admin_notes FROM copilot_queries_review WHERE id=?", (review_id,))
    updated_row = cursor.fetchone()
    assert updated_row["review_status"] == "reviewed"
    assert "SEBI-compliant" in updated_row["admin_notes"]
    conn.close()
    safe_print("PASS: Admin review updated successfully to 'reviewed' with audit notes.")

    # 8. S&R Levels & Indicator Endpoints Verification
    safe_print("\n--- TEST 8: S&R Levels & Indicators Health ---")
    status, sr_res = make_request("/api/sr-levels", method="GET")
    assert status == 200, f"SR levels failed: {sr_res}"
    assert "levels" in sr_res
    safe_print(f"PASS: S&R levels endpoint operational (Total levels: {len(sr_res.get('levels', []))}).")

    # 9. Verify All Department Module Imports
    safe_print("\n--- TEST 9: Department Architecture Integrity ---")
    import database
    import rag
    import indicators
    import temp_storage
    import broker
    import engine

    safe_print(f"PASS: database package OK ({database.__file__})")
    safe_print(f"PASS: rag package OK ({rag.__file__})")
    safe_print(f"PASS: indicators package OK ({indicators.__file__})")
    safe_print(f"PASS: temp_storage package OK ({temp_storage.__file__})")
    safe_print(f"PASS: broker package OK ({broker.__file__})")
    safe_print(f"PASS: engine package OK ({engine.__file__})")

    safe_print("\n" + "=" * 60)
    safe_print("ALL TESTS PASSED WITH 100% SUCCESS!")
    safe_print("=" * 60)


if __name__ == "__main__":
    run_tests()
