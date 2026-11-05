"""
database/user_db.py - High-Performance Multi-User Database Manager for NIFTY 50 Pro Terminal.
- Part of the Database Department.
- Uses SQLite with Write-Ahead Logging (WAL mode) for concurrency (zero database locking).
- Handles User Registration, Authentication (bcrypt), JWT Token issuance and verification.
- Manages User-Specific Drawings, Chat History, and Custom Indicator Preferences.
- Supports Admin Password Reset and User Management.
- Stores every user Copilot question in a dedicated per-user table (e.g. copilot_user_<username>)
  AND in a consolidated review table (copilot_queries_review) for admin review.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger("UserDB")

# Configuration
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DB_PATH = BASE_DIR / "users.db"
os.makedirs(DB_PATH.parent, exist_ok=True)
USERS_CSV_PATH = PROJECT_ROOT / "registered_users.csv"
USERS_CSV_BACKUP_PATH = BASE_DIR / "registered_users.csv"
LOGIN_RECORDS_CSV_PATH = PROJECT_ROOT / "user_login_records.csv"
LOGIN_RECORDS_CSV_BACKUP_PATH = BASE_DIR / "user_login_records.csv"
COPILOT_QUERIES_CSV_PATH = PROJECT_ROOT / "copilot_chat_queries.csv"
COPILOT_QUERIES_CSV_BACKUP_PATH = BASE_DIR / "copilot_chat_queries.csv"
VISITOR_ACTIVITY_CSV_PATH = PROJECT_ROOT / "visitor_daily_activity.csv"
VISITOR_ACTIVITY_CSV_BACKUP_PATH = BASE_DIR / "visitor_daily_activity.csv"

VISITOR_ACTIVITY_CSV_COLUMNS = [
    "Activity ID",
    "Timestamp (IST)",
    "Visitor ID",
    "Account / User",
    "Action",
    "Action Details",
    "IP Address",
    "City",
    "State / Region",
    "Country",
    "ISP / Network",
    "Device",
    "OS",
    "Browser",
    "Page Path"
]

COPILOT_CSV_COLUMNS = [
    "Query ID",
    "Timestamp (IST)",
    "Username",
    "User ID",
    "User Query",
    "AI Copilot Response",
    "Intent",
    "Market Price",
    "Timeframe",
    "Review Status",
    "Admin Notes",
    "Trading Style",
    "Confluence",
    "Client IP"
]

LOGIN_CSV_COLUMNS = [
    "Log ID",
    "Timestamp (IST)",
    "Event",
    "Status",
    "Mobile Number",
    "Username",
    "Email",
    "Role",
    "Trading Style",
    "IP Address",
    "User Agent",
    "Details",
    "User ID"
]

# Seamless migration: If database/users.db doesn't exist yet or is empty, copy from data_cache/users.db
legacy_db = PROJECT_ROOT / "data_cache" / "users.db"
if (not DB_PATH.exists() or DB_PATH.stat().st_size == 0) and legacy_db.exists() and legacy_db.stat().st_size > 0:
    try:
        shutil.copy2(str(legacy_db), str(DB_PATH))
        logger.info("Migrated legacy database from %s to %s", legacy_db, DB_PATH)
    except Exception as e:
        logger.warning("Failed to auto-migrate legacy db: %s", e)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "vwap-nifty-super-secret-jwt-key-2026-secure")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 30

ADMIN_MASTER_KEY = os.getenv("ADMIN_MASTER_KEY", "Rushit@Admin2026MasterKey")

# Database thread lock for safe serialized connection handling
_db_lock = threading.RLock()


def get_db_connection() -> sqlite3.Connection:
    """
    Creates an optimized SQLite connection with:
    - WAL Mode (Write-Ahead Logging) to prevent 'database is locked' errors.
    - 10-second busy timeout.
    - Synchronous=NORMAL for high write performance.
    """
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=10000;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()
    return conn


def get_user_psychology_profile(user_id: str) -> Dict[str, Any]:
    """Retrieves user behavioral and psychological profile or initializes default."""
    if not user_id:
        return {
            "discipline_score": 85,
            "emotional_state": "Disciplined",
            "overtrading_count": 0,
            "lunch_chop_trades": 0,
            "weaknesses": ["Chasing entries near ±2σ bands", "Trading during 11:30–13:15 Lunch Chop"],
            "strengths": ["Respects 1 Lot = 65 quantity rule", "Patient on Morning Prime breakouts"],
            "coaching_summary": "Maintain strict patience during lunch consolidation. Focus only on >5x touch S&R confluences."
        }
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
                u_row = cursor.fetchone()
                uname = u_row["username"] if u_row else "Trader"
                default_weaknesses = json.dumps(["Taking breakouts during Lunch Chop (11:30–13:15)", "Impatience at ±2σ exhaustion bands"])
                default_strengths = json.dumps(["Strictly adheres to 1 Lot (65 qty) sizing", "Waits for 5m candle confirmation"])
                cursor.execute("""
                    INSERT INTO user_psychology_profile 
                    (user_id, username, discipline_score, emotional_state, weaknesses, strengths, coaching_summary)
                    VALUES (?, ?, 85, 'Disciplined', ?, ?, 'Prioritize Morning Prime (09:30–11:30) and Afternoon (13:15–14:45) windows. Avoid Lunch Chop.')
                """, (user_id, uname, default_weaknesses, default_strengths))
                conn.commit()
                cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "discipline_score": row["discipline_score"],
                "risk_tolerance": row["risk_tolerance"],
                "emotional_state": row["emotional_state"],
                "overtrading_count": row["overtrading_count"],
                "revenge_trading_count": row["revenge_trading_count"],
                "lunch_chop_trades": row["lunch_chop_trades"],
                "weaknesses": json.loads(row["weaknesses"] or "[]"),
                "strengths": json.loads(row["strengths"] or "[]"),
                "coaching_summary": row["coaching_summary"] or "",
                "updated_at": str(row["updated_at"]),
            }
        except Exception as e:
            logger.error("Error fetching user psychology profile: %s", e)
            return {"discipline_score": 85, "emotional_state": "Disciplined"}
        finally:
            conn.close()


def update_user_psychology_profile(user_id: str, updates: Dict[str, Any]) -> bool:
    """Updates fields of user psychology profile."""
    if not user_id:
        return False
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            allowed = {"discipline_score", "risk_tolerance", "emotional_state", "overtrading_count", "revenge_trading_count", "lunch_chop_trades", "weaknesses", "strengths", "coaching_summary"}
            fields = []
            vals = []
            for k, v in updates.items():
                if k in allowed:
                    fields.append(f"{k} = ?")
                    vals.append(json.dumps(v) if isinstance(v, (list, dict)) else v)
            if not fields:
                return False
            from datetime import datetime
            vals.append(datetime.utcnow().isoformat())
            vals.append(user_id)
            cursor.execute(f"UPDATE user_psychology_profile SET {', '.join(fields)}, updated_at = ? WHERE user_id = ?", vals)
            conn.commit()
            return True
        except Exception as e:
            logger.error("Error updating psychology profile: %s", e)
            return False
        finally:
            conn.close()


def record_user_psychology_event(user_id: str, event_type: str, details: str) -> bool:
    """Records a behavioral event (e.g. Lunch Chop violation or discipline adherence)."""
    if not user_id:
        return False
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            from datetime import datetime
            cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                get_user_psychology_profile(user_id)
                cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

            score = int(row["discipline_score"] or 85)
            lc = int(row["lunch_chop_trades"] or 0)
            ot = int(row["overtrading_count"] or 0)
            rv = int(row["revenge_trading_count"] or 0)
            ev_list = json.loads(row["history_events"] or "[]")
            ev_list.append({"time": datetime.utcnow().isoformat(), "type": event_type, "details": details})
            ev_list = ev_list[-30:]

            if event_type == "LUNCH_CHOP_ENTRY":
                lc += 1
                score = max(30, score - 6)
            elif event_type == "REVENGE_TRADE":
                rv += 1
                score = max(20, score - 10)
            elif event_type == "OVERTRADING":
                ot += 1
                score = max(30, score - 5)
            elif event_type == "DISCIPLINE_FOLLOWED":
                score = min(100, score + 4)

            cursor.execute("""
                UPDATE user_psychology_profile 
                SET discipline_score = ?, lunch_chop_trades = ?, overtrading_count = ?, revenge_trading_count = ?, history_events = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (score, lc, ot, rv, json.dumps(ev_list), user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error("Error recording psychology event: %s", e)
            return False
        finally:
            conn.close()


# ==============================================================
# 👑 Comprehensive Admin User & Guest Command Center Functions
# ==============================================================

def add_active_display_time(visitor_id: str, user_id: Optional[str] = None, seconds: int = 15):
    """Accumulates active on-screen display time (seconds) for user and visitor session."""
    sec = max(1, min(60, int(seconds)))
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    UPDATE users 
                    SET total_active_seconds = COALESCE(total_active_seconds, 0) + ? 
                    WHERE id = ? OR username = ?
                """, (sec, user_id, user_id))

            if visitor_id:
                cursor.execute("""
                    UPDATE visitor_identities 
                    SET total_active_seconds = COALESCE(total_active_seconds, 0) + ? 
                    WHERE visitor_id = ?
                """, (sec, visitor_id))
            conn.commit()
        except Exception as e:
            logger.debug("Error adding active display time: %s", e)
        finally:
            conn.close()


def freeze_user_admin(user_id: str, reason: str = "") -> Tuple[bool, str]:
    """Freezes/suspends a registered user account."""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role FROM users WHERE id = ? OR username = ?", (user_id, user_id))
            user = cursor.fetchone()
            if not user:
                return False, f"User '{user_id}' not found."
            if user["role"] == "admin":
                return False, "Cannot freeze system administrator account."

            uid = user["id"]
            uname = user["username"]
            freeze_msg = reason.strip() or "Irregular activity, bad requests, or misuse of this website"
            now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                UPDATE users
                SET is_frozen = 1, freeze_reason = ?, frozen_at = ?
                WHERE id = ?
            """, (freeze_msg, now_utc, uid))
            conn.commit()
            logger.info("Admin froze user %s (%s): %s", uname, uid, freeze_msg)
            return True, f"User '{uname}' has been frozen/blocked."
        except Exception as e:
            logger.error("Error freezing user: %s", e)
            return False, str(e)
        finally:
            conn.close()


def unfreeze_user_admin(user_id: str) -> Tuple[bool, str]:
    """Unfreezes/restores a registered user account."""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET is_frozen = 0, freeze_reason = '', frozen_at = NULL
                WHERE id = ? OR username = ?
            """, (user_id, user_id))
            conn.commit()
            return True, "User account unblocked and restored successfully."
        except Exception as e:
            logger.error("Error unfreezing user: %s", e)
            return False, str(e)
        finally:
            conn.close()


def is_user_frozen(user_id: str) -> Tuple[bool, str]:
    """Checks if a user account is currently frozen/blocked."""
    if not user_id:
        return False, ""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT is_frozen, freeze_reason FROM users WHERE id = ? OR username = ?", (user_id, user_id))
            row = cursor.fetchone()
            if row and row["is_frozen"]:
                return True, row["freeze_reason"] or "Irregular activity, bad requests, or misuse of this website"
            return False, ""
        finally:
            conn.close()


def block_ip_admin(ip_address: str, reason: str = "") -> Tuple[bool, str]:
    """Blocks an IP address from accessing the platform."""
    clean_ip = (ip_address or "").strip()
    if not clean_ip:
        return False, "IP address required"
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            block_msg = reason.strip() or "Irregular activity, bad requests, or misuse of this website"
            cursor.execute("""
                INSERT OR REPLACE INTO blocked_ips (ip_address, reason, blocked_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (clean_ip, block_msg))
            conn.commit()
            logger.info("Admin blocked IP: %s (Reason: %s)", clean_ip, block_msg)
            return True, f"IP '{clean_ip}' has been blocked."
        except Exception as e:
            logger.error("Error blocking IP: %s", e)
            return False, str(e)
        finally:
            conn.close()


def unblock_ip_admin(ip_address: str) -> Tuple[bool, str]:
    """Unblocks an IP address."""
    clean_ip = (ip_address or "").strip()
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blocked_ips WHERE ip_address = ?", (clean_ip,))
            conn.commit()
            logger.info("Admin unblocked IP: %s", clean_ip)
            return True, f"IP '{clean_ip}' unblocked successfully."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()


def is_ip_blocked(ip_address: str) -> Tuple[bool, str]:
    """Checks if an IP address is blocked."""
    clean_ip = (ip_address or "").strip()
    if not clean_ip or clean_ip in ("127.0.0.1", "localhost"):
        return False, ""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT reason FROM blocked_ips WHERE ip_address = ?", (clean_ip,))
            row = cursor.fetchone()
            if row:
                return True, row["reason"] or "Irregular activity, bad requests, or misuse of this website"
            return False, ""
        finally:
            conn.close()


def get_blocked_entities_admin() -> Dict[str, Any]:
    """Returns all currently blocked users and IPs."""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, phone, freeze_reason, frozen_at FROM users WHERE is_frozen = 1")
            frozen_users = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT ip_address, reason, blocked_at FROM blocked_ips ORDER BY blocked_at DESC")
            blocked_ips = [dict(r) for r in cursor.fetchall()]

            return {"frozen_users": frozen_users, "blocked_ips": blocked_ips}
        finally:
            conn.close()


def delete_user_completely_admin(user_id: str) -> Tuple[bool, str]:
    """
    Completely and permanently purges a user and ALL their data from the platform:
    1. users record
    2. user_drawings
    3. chat_history
    4. copilot_queries_review (queries asked by this user)
    5. user_preferences
    6. user_login_records
    7. trade_predictions
    8. user_psychology_profile
    9. drops copilot_user_<username> dedicated table
    10. unlinks from visitor_identities
    11. visitor_activity_log
    """
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role FROM users WHERE id = ? OR username = ?", (user_id, user_id))
            user = cursor.fetchone()
            if not user:
                return False, f"User '{user_id}' not found."

            uid = user["id"]
            uname = user["username"]
            if user["role"] == "admin":
                return False, "Cannot delete master system administrator account."

            # Delete drawings
            cursor.execute("DELETE FROM user_drawings WHERE user_id = ?", (uid,))
            # Delete chat history
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (uid,))
            # Delete copilot queries review
            cursor.execute("DELETE FROM copilot_queries_review WHERE user_id = ? OR username = ?", (uid, uname))
            # Delete preferences
            cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (uid,))
            # Delete login records
            cursor.execute("DELETE FROM user_login_records WHERE user_id = ? OR username = ?", (uid, uname))
            # Delete predictions
            try:
                cursor.execute("DELETE FROM trade_predictions WHERE user_id = ?", (uid,))
            except Exception:
                pass
            # Delete psychology profile
            try:
                cursor.execute("DELETE FROM user_psychology_profile WHERE user_id = ?", (uid,))
            except Exception:
                pass
            # Unlink visitor identities
            cursor.execute("UPDATE visitor_identities SET user_id = NULL, has_account = 0 WHERE user_id = ?", (uid,))
            # Delete activity log
            cursor.execute("DELETE FROM visitor_activity_log WHERE user_id = ? OR username = ?", (uid, uname))
            # Drop dedicated copilot table
            table_name = f"copilot_user_{uname.replace('-', '_')}"
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            # Finally delete from users
            cursor.execute("DELETE FROM users WHERE id = ?", (uid,))

            conn.commit()
            logger.info("Admin permanently purged user %s (%s) and all associated data.", uname, uid)
            return True, f"User '{uname}' and all associated drawings, chat history, and logs permanently deleted."
        except Exception as e:
            logger.error("Error purging user: %s", e)
            return False, str(e)
        finally:
            conn.close()


def delete_guest_completely_admin(visitor_id: str) -> Tuple[bool, str]:
    """Permanently deletes a guest visitor record, pageviews, and activity log."""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM visitor_activity_log WHERE visitor_id = ?", (visitor_id,))
            cursor.execute("DELETE FROM site_pageviews WHERE visitor_id = ?", (visitor_id,))
            cursor.execute("DELETE FROM visitor_identities WHERE visitor_id = ?", (visitor_id,))
            conn.commit()
            return True, f"Guest visitor '{visitor_id}' records deleted successfully."
        except Exception as e:
            logger.error("Error deleting guest: %s", e)
            return False, str(e)
        finally:
            conn.close()


def get_all_registered_users_admin() -> List[Dict[str, Any]]:
    """Returns all registered users with display active time, profile, drawings count, and freeze status."""
    import pandas as pd
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    u.id, u.username, u.email, u.phone, u.role, u.trading_style,
                    u.is_frozen, u.freeze_reason, u.frozen_at,
                    u.total_active_seconds, u.accepted_ip, u.created_at, u.last_login,
                    COUNT(DISTINCT d.id) as drawings_count,
                    COUNT(DISTINCT q.id) as copilot_queries_count
                FROM users u
                LEFT JOIN user_drawings d ON u.id = d.user_id
                LEFT JOIN copilot_queries_review q ON (u.id = q.user_id OR u.username = q.username)
                GROUP BY u.id
                ORDER BY u.created_at DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                # Format dates to IST
                for dt_col in ["created_at", "last_login", "frozen_at"]:
                    val = d.get(dt_col)
                    if val:
                        try:
                            ist_dt = pd.to_datetime(val) + timedelta(hours=5, minutes=30)
                            d[f"{dt_col}_ist"] = ist_dt.strftime("%d-%b-%Y %I:%M:%S %p")
                        except Exception:
                            d[f"{dt_col}_ist"] = str(val)
                    else:
                        d[f"{dt_col}_ist"] = "--"

                # Format total display active time
                total_sec = d.get("total_active_seconds") or 0
                hrs = total_sec // 3600
                mins = (total_sec % 3600) // 60
                d["active_display_str"] = f"{hrs}h {mins}m" if hrs > 0 else f"{mins} mins"


                results.append(d)
            return results
        finally:
            conn.close()


def get_user_timeline_activity_admin(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves full chronological activity timeline for a registered user:
    Registration, Logins, AI Copilot Questions, Drawings, Indicator toggles, Timeframe changes.
    """
    import pandas as pd
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, phone, created_at, accepted_ip, trading_style, total_active_seconds, is_frozen, freeze_reason FROM users WHERE id = ? OR username = ?", (user_id, user_id))
            user = cursor.fetchone()
            if not user:
                return []
            uid = user["id"]
            uname = user["username"]

            timeline = []

            # 1. Registration event
            reg_time = user["created_at"]
            try:
                reg_ist = (pd.to_datetime(reg_time) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M:%S %p")
            except Exception:
                reg_ist = str(reg_time)
            timeline.append({
                "timestamp": reg_time,
                "timestamp_ist": reg_ist,
                "type": "account_created",
                "icon": "🎉",
                "title": "Account Registered",
                "details": f"Registered with mobile {user['phone']} and style {user['trading_style']}",
                "ip": user["accepted_ip"] or ""
            })

            # 2. Login events
            cursor.execute("SELECT created_at, event_type, status, ip_address, details FROM user_login_records WHERE user_id = ? OR username = ? ORDER BY created_at DESC LIMIT 50", (uid, uname))
            for l_row in cursor.fetchall():
                t = l_row["created_at"]
                try:
                    t_ist = (pd.to_datetime(t) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception:
                    t_ist = str(t)
                timeline.append({
                    "timestamp": t,
                    "timestamp_ist": t_ist,
                    "type": "login_event",
                    "icon": "🔑",
                    "title": f"Login {l_row['status'].title()}",
                    "details": l_row["details"] or "User session authenticated",
                    "ip": l_row["ip_address"] or ""
                })

            # 3. AI Copilot Queries
            cursor.execute("SELECT created_at, query, response, market_price, timeframe, metadata FROM copilot_queries_review WHERE user_id = ? OR username = ? ORDER BY created_at DESC LIMIT 100", (uid, uname))
            for q_row in cursor.fetchall():
                t = q_row["created_at"]
                try:
                    t_ist = (pd.to_datetime(t) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception:
                    t_ist = str(t)
                q_meta = {}
                if q_row["metadata"]:
                    try: q_meta = json.loads(q_row["metadata"])
                    except Exception: pass
                timeline.append({
                    "timestamp": t,
                    "timestamp_ist": t_ist,
                    "type": "copilot_query",
                    "icon": "🤖",
                    "title": "Asked AI Strategy Copilot",
                    "details": f'Query: "{q_row["query"]}" (Price: ₹{float(q_row["market_price"] or 0):,.2f}, TF: {q_row["timeframe"]})',
                    "response": q_row["response"],
                    "ip": q_meta.get("client_ip", "")
                })

            # 4. Chart Drawings
            cursor.execute("SELECT created_at, drawing_type, price1, price2, remark FROM user_drawings WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (uid,))
            for d_row in cursor.fetchall():
                t = d_row["created_at"]
                try:
                    t_ist = (pd.to_datetime(t) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception:
                    t_ist = str(t)
                timeline.append({
                    "timestamp": t,
                    "timestamp_ist": t_ist,
                    "type": "chart_drawing",
                    "icon": "🎨",
                    "title": f"Drew {d_row['drawing_type'].replace('_', ' ').title()}",
                    "details": f"P1: ₹{float(d_row['price1'] or 0):,.2f}" + (f", P2: ₹{float(d_row['price2'] or 0):,.2f}" if d_row["price2"] else "") + (f" ({d_row['remark']})" if d_row["remark"] else ""),
                    "ip": ""
                })

            # 5. Granular visitor activities
            cursor.execute("SELECT created_at, action_type, action_detail, ip_address, city, isp, device_type FROM visitor_activity_log WHERE user_id = ? OR username = ? ORDER BY created_at DESC LIMIT 100", (uid, uname))
            for a_row in cursor.fetchall():
                t = a_row["created_at"]
                try:
                    t_ist = (pd.to_datetime(t) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception:
                    t_ist = str(t)
                icon = {
                    "timeframe_switch": "⏱️",
                    "indicator_toggle": "📊",
                    "sr_toggle": "🛡️",
                    "tool_open": "🛠️",
                    "developer_contact_open": "💬",
                    "page_view": "👁️"
                }.get(a_row["action_type"], "⚡")
                timeline.append({
                    "timestamp": t,
                    "timestamp_ist": t_ist,
                    "type": a_row["action_type"],
                    "icon": icon,
                    "title": a_row["action_type"].replace("_", " ").title(),
                    "details": a_row["action_detail"] or a_row["action_type"],
                    "ip": a_row["ip_address"] or "",
                    "location": f"{a_row['city']} ({a_row['isp']})" if a_row["city"] else ""
                })

            timeline.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
            return timeline
        finally:
            conn.close()


def get_guest_timeline_activity_admin(visitor_id: str) -> List[Dict[str, Any]]:
    """Retrieves full chronological activity timeline for an anonymous guest visitor."""
    import pandas as pd
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            timeline = []

            # 1. Granular visitor activity
            cursor.execute("SELECT created_at, action_type, action_detail, ip_address, city, isp, device_type, os_name, browser FROM visitor_activity_log WHERE visitor_id = ? ORDER BY created_at DESC LIMIT 150", (visitor_id,))
            for a_row in cursor.fetchall():
                t = a_row["created_at"]
                try:
                    t_ist = (pd.to_datetime(t) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception:
                    t_ist = str(t)
                icon = {
                    "timeframe_switch": "⏱️",
                    "indicator_toggle": "📊",
                    "sr_toggle": "🛡️",
                    "tool_open": "🛠️",
                    "developer_contact_open": "💬",
                    "page_view": "👁️"
                }.get(a_row["action_type"], "⚡")
                timeline.append({
                    "timestamp": t,
                    "timestamp_ist": t_ist,
                    "type": a_row["action_type"],
                    "icon": icon,
                    "title": a_row["action_type"].replace("_", " ").title(),
                    "details": a_row["action_detail"] or a_row["action_type"],
                    "ip": a_row["ip_address"] or "",
                    "location": f"{a_row['city']} ({a_row['isp']})" if a_row["city"] else ""
                })

            # 2. Pageviews
            cursor.execute("SELECT timestamp, path, referrer FROM site_pageviews WHERE visitor_id = ? ORDER BY timestamp DESC LIMIT 50", (visitor_id,))
            for p_row in cursor.fetchall():
                t = p_row["timestamp"]
                try:
                    t_ist = (pd.to_datetime(t) + timedelta(hours=5, minutes=30)).strftime("%d-%b-%Y %I:%M:%S %p")
                except Exception:
                    t_ist = str(t)
                timeline.append({
                    "timestamp": t,
                    "timestamp_ist": t_ist,
                    "type": "page_view",
                    "icon": "👁️",
                    "title": "Page View",
                    "details": f"Path: {p_row['path']}" + (f" (from {p_row['referrer']})" if p_row['referrer'] else ""),
                    "ip": ""
                })

            timeline.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
            return timeline
        finally:
            conn.close()


def get_all_guests_admin(limit: int = 100) -> List[Dict[str, Any]]:
    """Returns all guest visitors with IP location, device, display active time, and block status."""
    import pandas as pd
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    v.visitor_id, v.first_seen, v.last_seen, v.device_type, v.browser,
                    v.ip_address, v.visit_count, v.city, v.region, v.country, v.org_isp,
                    v.os_name, v.total_active_seconds,
                    b.reason as block_reason,
                    CASE WHEN b.ip_address IS NOT NULL THEN 1 ELSE 0 END as is_blocked,
                    COUNT(DISTINCT a.id) as actions_count
                FROM visitor_identities v
                LEFT JOIN blocked_ips b ON v.ip_address = b.ip_address
                LEFT JOIN visitor_activity_log a ON v.visitor_id = a.visitor_id
                WHERE (v.user_id IS NULL OR v.has_account = 0)
                GROUP BY v.visitor_id
                ORDER BY v.last_seen DESC
                LIMIT ?
            """
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                for dt_col in ["first_seen", "last_seen"]:
                    val = d.get(dt_col)
                    if val:
                        try:
                            ist_dt = pd.to_datetime(val) + timedelta(hours=5, minutes=30)
                            d[f"{dt_col}_ist"] = ist_dt.strftime("%d-%b %I:%M %p")
                        except Exception:
                            d[f"{dt_col}_ist"] = str(val)
                    else:
                        d[f"{dt_col}_ist"] = "--"

                total_sec = d.get("total_active_seconds") or 0
                hrs = total_sec // 3600
                mins = (total_sec % 3600) // 60
                d["active_display_str"] = f"{hrs}h {mins}m" if hrs > 0 else f"{mins} mins"

                city = d.get("city") or ""
                region = d.get("region") or ""
                d["location_str"] = f"{city}, {region}" if city and region else (city or region or "India")
                results.append(d)
            return results
        finally:
            conn.close()


def init_database():
    """Initializes all database tables and seeds the master admin user if not present."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'trader',
            trading_style TEXT DEFAULT 'intraday_scalper',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        """)

        # 2. User Drawings Table (1-to-many: User has many drawings)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_drawings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            drawing_id TEXT NOT NULL,
            drawing_type TEXT NOT NULL,
            price1 REAL,
            price2 REAL,
            remark TEXT,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_drawings_user_id ON user_drawings(user_id);")

        # Ensure policy acceptance audit columns exist in users table
        for col, col_type in [
            ("accepted_policy", "INTEGER DEFAULT 0"),
            ("policy_accepted_at", "TIMESTAMP"),
            ("policy_version", "TEXT DEFAULT 'v2.0_sebi_full'"),
            ("accepted_ip", "TEXT DEFAULT '127.0.0.1'"),
            ("phone", "TEXT DEFAULT ''"),
            ("is_frozen", "INTEGER DEFAULT 0"),
            ("freeze_reason", "TEXT DEFAULT ''"),
            ("frozen_at", "TIMESTAMP"),
            ("total_active_seconds", "INTEGER DEFAULT 0")
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type};")
            except Exception:
                pass  # Column already exists

        # 3. User Chat History Table (Conversational memory per user)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_history(user_id);")

        # 4. User Preferences Table (Custom indicators, theme, settings)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            active_indicators TEXT,
            theme TEXT DEFAULT 'dark',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 5. Master Copilot Queries Review Table (Consolidated audit and review)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS copilot_queries_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            user_table TEXT NOT NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            intent TEXT,
            market_price REAL,
            timeframe TEXT DEFAULT '5m',
            review_status TEXT DEFAULT 'pending',
            admin_notes TEXT DEFAULT '',
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_copilot_review_created ON copilot_queries_review(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_copilot_review_status ON copilot_queries_review(review_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_copilot_review_username ON copilot_queries_review(username);")

        # 8. Visitor Activity Log Table (Granular daily actions & IP tracking)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitor_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT NOT NULL,
            user_id TEXT,
            username TEXT DEFAULT 'Guest',
            action_type TEXT NOT NULL,
            action_detail TEXT DEFAULT '',
            path TEXT DEFAULT '/',
            ip_address TEXT DEFAULT '',
            city TEXT DEFAULT '',
            region TEXT DEFAULT '',
            country TEXT DEFAULT 'IN',
            isp TEXT DEFAULT '',
            device_type TEXT DEFAULT 'Desktop',
            os_name TEXT DEFAULT '',
            browser TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_created ON visitor_activity_log(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_visitor ON visitor_activity_log(visitor_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_ip ON visitor_activity_log(ip_address);")

        # Ensure location and OS columns exist in visitor_identities
        for v_col, v_type in [
            ("city", "TEXT DEFAULT ''"),
            ("region", "TEXT DEFAULT ''"),
            ("country", "TEXT DEFAULT 'IN'"),
            ("org_isp", "TEXT DEFAULT ''"),
            ("os_name", "TEXT DEFAULT ''"),
            ("total_active_seconds", "INTEGER DEFAULT 0")
        ]:
            try:
                cursor.execute(f"ALTER TABLE visitor_identities ADD COLUMN {v_col} {v_type};")
            except Exception:
                pass

        # 9. Blocked IPs Table (Admin IP banning)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocked_ips (
            ip_address TEXT PRIMARY KEY,
            reason TEXT DEFAULT 'Irregular activity, bad requests, or misuse of this website',
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            blocked_by TEXT DEFAULT 'admin'
        );
        """)

        # Ensure user_cleared_display column exists in copilot_queries_review for developer auditing
        try:
            cursor.execute("PRAGMA table_info(copilot_queries_review)")
            cols = [r["name"] for r in cursor.fetchall()]
            if "user_cleared_display" not in cols:
                cursor.execute("ALTER TABLE copilot_queries_review ADD COLUMN user_cleared_display INTEGER DEFAULT 0")
        except Exception as e:
            logger.debug("Migration check for copilot_queries_review: %s", e)

        # Ensure hidden_from_user column exists in all dedicated copilot_user_% tables
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'copilot_user_%'")
            user_tables = [r["name"] for r in cursor.fetchall()]
            for t in user_tables:
                cursor.execute(f"PRAGMA table_info({t})")
                t_cols = [r["name"] for r in cursor.fetchall()]
                if "hidden_from_user" not in t_cols:
                    cursor.execute(f"ALTER TABLE {t} ADD COLUMN hidden_from_user INTEGER DEFAULT 0")
        except Exception as e:
            logger.debug("Migration check for copilot_user tables: %s", e)

        # 6. Common Trade Predictions & Learning Journal Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_predictions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            username TEXT DEFAULT 'Trader',
            source TEXT NOT NULL,
            symbol TEXT DEFAULT 'NIFTY 50',
            timeframe TEXT DEFAULT '5m',
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            target_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            rr_ratio REAL,
            predicted_pnl_pts REAL,
            predicted_pnl_pct REAL,
            status TEXT DEFAULT 'ACTIVE',
            exit_price REAL,
            exit_time TEXT,
            actual_pnl_pts REAL,
            actual_pnl_pct REAL,
            pnl_error_pts REAL,
            mae_pts REAL DEFAULT 0.0,
            mfe_pts REAL DEFAULT 0.0,
            error_category TEXT,
            error_analysis TEXT,
            reflection_text TEXT,
            market_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_status ON trade_predictions(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_created ON trade_predictions(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_user ON trade_predictions(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_source ON trade_predictions(source);")

        # 7. User Psychology & Behavioral Profile Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_psychology_profile (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            discipline_score INTEGER DEFAULT 85,
            risk_tolerance TEXT DEFAULT 'moderate',
            emotional_state TEXT DEFAULT 'disciplined',
            overtrading_count INTEGER DEFAULT 0,
            revenge_trading_count INTEGER DEFAULT 0,
            lunch_chop_trades INTEGER DEFAULT 0,
            weaknesses TEXT DEFAULT '[]',
            strengths TEXT DEFAULT '[]',
            coaching_summary TEXT DEFAULT '',
            history_events TEXT DEFAULT '[]',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_psych_user ON user_psychology_profile(user_id);")

        # 8. User Login & Account Activity Audit Trail Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_login_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT NOT NULL,
            email TEXT DEFAULT '',
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            role TEXT DEFAULT 'trader',
            trading_style TEXT DEFAULT '',
            ip_address TEXT DEFAULT '127.0.0.1',
            user_agent TEXT DEFAULT '',
            details TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_records_created ON user_login_records(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_records_user ON user_login_records(username);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);")

        try:
            cursor.execute("ALTER TABLE user_login_records ADD COLUMN phone TEXT DEFAULT '';")
        except Exception:
            pass

        # 9. Real-Time Mobile OTP Verification Codes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            purpose TEXT DEFAULT 'login',
            expires_at TIMESTAMP NOT NULL,
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_verification_codes(phone, created_at DESC);")

        # 10. Visitor Identities Table (Unique device/browser tracking)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitor_identities (
            visitor_id TEXT PRIMARY KEY,
            first_seen TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            user_id TEXT DEFAULT NULL,
            has_account INTEGER DEFAULT 0,
            device_type TEXT DEFAULT 'Desktop',
            browser TEXT DEFAULT 'Unknown',
            ip_address TEXT DEFAULT '',
            visit_count INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis_last_seen ON visitor_identities(last_seen DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis_has_acc ON visitor_identities(has_account);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis_user_id ON visitor_identities(user_id);")

        # 11. Site Pageviews Table (Granular page hit logs)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_pageviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            path TEXT DEFAULT '/',
            referrer TEXT DEFAULT '',
            FOREIGN KEY (visitor_id) REFERENCES visitor_identities(visitor_id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pageviews_ts ON site_pageviews(timestamp DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pageviews_vis ON site_pageviews(visitor_id);")

        # 14. User Feedback & Support Messages Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT DEFAULT 'guest',
            username TEXT DEFAULT 'Guest Trader',
            email TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            message TEXT NOT NULL,
            status TEXT DEFAULT 'unread',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON user_feedback(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_status ON user_feedback(status);")

        # Seed master admin if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin' OR email = 'admin@vwapterminal.com'")
        admin_row = cursor.fetchone()
        if not admin_row:
            admin_id = "usr_admin_001"
            pw_hash = hash_password("123@Qweasd")
            cursor.execute(
                "INSERT INTO users (id, username, email, password_hash, role, trading_style) VALUES (?, ?, ?, ?, ?, ?)",
                (admin_id, "admin", "admin@vwapterminal.com", pw_hash, "admin", "intraday_scalper")
            )
            logger.info("Initialized default master admin account ('admin' / '123@Qweasd')")

        # Strict security compliance: Purge any legacy plain_password data
        try:
            cursor.execute("UPDATE users SET plain_password = NULL WHERE plain_password IS NOT NULL")
        except Exception:
            pass

        conn.commit()
        conn.close()
        logger.info("Multi-User SQLite database verified with WAL mode at %s", DB_PATH)
        try:
            sync_users_to_csv()
        except Exception as e_c:
            logger.warning("Initial users CSV sync note: %s", e_c)
        try:
            sync_login_records_to_csv()
        except Exception as e_l:
            logger.warning("Initial login records CSV sync note: %s", e_l)


# --- Password Hashing & JWT Utilities ---

def hash_password(password: str) -> str:
    """Hashes a password securely using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error("Password verification error: %s", e)
        return False


def create_access_token(user_id: str, username: str, role: str, trading_style: str) -> str:
    """Creates a signed JSON Web Token (JWT) with 30-day validity."""
    expires = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "trading_style": trading_style,
        "exp": expires
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token. Returns payload dict or None if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
    except Exception as e:
        logger.warning("Token decode error: %s", e)
        return None


# --- User Management CRUD ---



def sync_users_to_csv(csv_path: Optional[Path] = None) -> str:
    """
    Exports all registered user details from SQLite database into an easily readable CSV file.
    Stores in both project root (registered_users.csv) and database/ folder.
    Excludes sensitive password hashes; includes human-readable IST timestamps and policy records.
    """
    try:
        import pandas as pd
        with _db_lock:
            conn = get_db_connection()
            query = """
                SELECT 
                    id, username, email, phone, role, trading_style, created_at, last_login, accepted_policy, policy_accepted_at, policy_version, accepted_ip
                FROM users 
                ORDER BY created_at DESC
            """
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

        if not rows:
            return ""

        data = []
        for r in rows:
            d = dict(r)
            for col_utc, col_ist in [('created_at', 'Registration Date (IST)'), ('last_login', 'Last Login (IST)'), ('policy_accepted_at', 'Policy Accepted Date (IST)')]:
                val = d.get(col_utc)
                if val:
                    try:
                        dt = pd.to_datetime(val)
                        dt_ist = dt + timedelta(hours=5, minutes=30)
                        d[col_ist] = dt_ist.strftime('%d-%b-%Y %I:%M:%S %p')
                    except Exception:
                        d[col_ist] = str(val)
                else:
                    d[col_ist] = '--'

            style_names = {
                'intraday_scalper': 'Intraday Scalper',
                'day_trader': 'Day Trader',
                'swing_trader': 'Swing Trader',
                'options_buyer': 'Options Buyer'
            }
            raw_style = d.get('trading_style', 'intraday_scalper')
            d['Trading Style'] = style_names.get(raw_style, str(raw_style).replace('_', ' ').title())
            d['Role'] = str(d.get('role', 'trader')).upper()
            d['SEBI Policy Accepted'] = 'YES (Agreed)' if d.get('accepted_policy') == 1 else 'NO'
            d['User ID'] = d.get('id')
            d['Username'] = d.get('username')
            d['Mobile Number'] = d.get('phone') or '--'
            d['Email'] = d.get('email')
            d['IP Address'] = d.get('accepted_ip') or '127.0.0.1'
            d['Policy Version'] = d.get('policy_version') or 'v2.0_sebi_full'
            data.append(d)

        df = pd.DataFrame(data)
        cols = [
            'Username',
            'Mobile Number',
            'Email',
            'Registration Date (IST)',
            'Trading Style',
            'Role',
            'Last Login (IST)',
            'SEBI Policy Accepted',
            'IP Address',
            'User ID',
            'Policy Version',
            'Policy Accepted Date (IST)'
        ]
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]

        out_path = csv_path or USERS_CSV_PATH
        df.to_csv(str(out_path), index=False, encoding='utf-8-sig')

        # Also write backup copy in database/ folder
        if USERS_CSV_BACKUP_PATH != out_path:
            df.to_csv(str(USERS_CSV_BACKUP_PATH), index=False, encoding='utf-8-sig')

        logger.info("Successfully synced %d registered users to CSV: %s", len(df), out_path)
        return str(out_path)
    except Exception as e:
        logger.error("Error syncing registered users to CSV: %s", e)
        return ""

def append_login_record_to_csv(row_dict: Dict[str, Any]):
    """Appends a single login/registration activity record in real-time to user_login_records.csv."""
    try:
        import csv
        for target_path in [LOGIN_RECORDS_CSV_PATH, LOGIN_RECORDS_CSV_BACKUP_PATH]:
            file_exists = target_path.exists() and target_path.stat().st_size > 0
            with open(target_path, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(LOGIN_CSV_COLUMNS)
                writer.writerow([
                    row_dict.get("Log ID", ""),
                    row_dict.get("Timestamp (IST)", ""),
                    row_dict.get("Event", ""),
                    row_dict.get("Status", ""),
                    row_dict.get("Mobile Number", ""),
                    row_dict.get("Username", ""),
                    row_dict.get("Email", ""),
                    row_dict.get("Role", ""),
                    row_dict.get("Trading Style", ""),
                    row_dict.get("IP Address", ""),
                    row_dict.get("User Agent", ""),
                    row_dict.get("Details", ""),
                    row_dict.get("User ID", ""),
                ])
    except Exception as e:
        logger.warning("Error live-appending to user_login_records.csv: %s", e)


def record_login_activity(
    user_id: str,
    username: str,
    email: str = "",
    phone: str = "",
    event_type: str = "LOGIN_SUCCESS",
    status: str = "SUCCESS",
    role: str = "trader",
    trading_style: str = "",
    ip_address: str = "127.0.0.1",
    user_agent: str = "",
    details: str = ""
) -> int:
    """
    Records a user login or account creation event in the SQLite database
    and immediately live-updates the user_login_records.csv file.
    """
    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    ist_str = now_ist.strftime("%d-%b-%Y %I:%M:%S %p")

    style_names = {
        'intraday_scalper': 'Intraday Scalper',
        'day_trader': 'Day Trader',
        'swing_trader': 'Swing Trader',
        'options_buyer': 'Options Buyer'
    }
    pretty_style = style_names.get(trading_style, str(trading_style).replace('_', ' ').title()) if trading_style else ""

    record_id = 0
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_login_records (user_id, username, email, phone, event_type, status, role, trading_style, ip_address, user_agent, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (user_id, username, email, phone, event_type, status, role, trading_style, ip_address, user_agent, details)
            )
            conn.commit()
            record_id = cursor.lastrowid
        except Exception as e:
            logger.error("Error inserting login record to db: %s", e)
        finally:
            conn.close()

    # Real-time live update into CSV
    row_data = {
        "Log ID": record_id,
        "Timestamp (IST)": ist_str,
        "Event": event_type,
        "Status": status,
        "Mobile Number": phone or "--",
        "Username": username,
        "Email": email,
        "Role": role.upper() if role else "TRADER",
        "Trading Style": pretty_style,
        "IP Address": ip_address,
        "User Agent": user_agent,
        "Details": details,
        "User ID": user_id,
    }
    append_login_record_to_csv(row_data)
    return record_id


def sync_login_records_to_csv(csv_path: Optional[Path] = None) -> str:
    """
    Exports all login and registration records from SQLite database into user_login_records.csv.
    Stores in both project root and database/ folder.
    """
    try:
        import pandas as pd
        with _db_lock:
            conn = get_db_connection()
            query = """
                SELECT id, user_id, username, email, phone, event_type, status, role, trading_style, ip_address, user_agent, details, created_at
                FROM user_login_records
                ORDER BY created_at DESC
            """
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

        target_path = csv_path or LOGIN_RECORDS_CSV_PATH
        if not rows:
            df_empty = pd.DataFrame(columns=LOGIN_CSV_COLUMNS)
            df_empty.to_csv(str(target_path), index=False, encoding='utf-8-sig')
            if LOGIN_RECORDS_CSV_BACKUP_PATH != target_path:
                df_empty.to_csv(str(LOGIN_RECORDS_CSV_BACKUP_PATH), index=False, encoding='utf-8-sig')
            return str(target_path)

        style_names = {
            'intraday_scalper': 'Intraday Scalper',
            'day_trader': 'Day Trader',
            'swing_trader': 'Swing Trader',
            'options_buyer': 'Options Buyer'
        }

        data = []
        for r in rows:
            d = dict(r)
            created_val = d.get('created_at')
            if created_val:
                try:
                    dt = pd.to_datetime(created_val)
                    dt_ist = dt + timedelta(hours=5, minutes=30)
                    ist_str = dt_ist.strftime('%d-%b-%Y %I:%M:%S %p')
                except Exception:
                    ist_str = str(created_val)
            else:
                ist_str = '--'

            raw_style = d.get('trading_style', '')
            pretty_style = style_names.get(raw_style, str(raw_style).replace('_', ' ').title()) if raw_style else ''

            data.append({
                "Log ID": d.get("id"),
                "Timestamp (IST)": ist_str,
                "Event": d.get("event_type", ""),
                "Status": d.get("status", ""),
                "Mobile Number": d.get("phone") or "--",
                "Username": d.get("username", ""),
                "Email": d.get("email", ""),
                "Role": str(d.get("role", "trader")).upper(),
                "Trading Style": pretty_style,
                "IP Address": d.get("ip_address") or "127.0.0.1",
                "User Agent": d.get("user_agent") or "",
                "Details": d.get("details", ""),
                "User ID": d.get("user_id", ""),
            })

        df = pd.DataFrame(data)
        df = df[LOGIN_CSV_COLUMNS]

        df.to_csv(str(target_path), index=False, encoding='utf-8-sig')
        if LOGIN_RECORDS_CSV_BACKUP_PATH != target_path:
            df.to_csv(str(LOGIN_RECORDS_CSV_BACKUP_PATH), index=False, encoding='utf-8-sig')

        logger.info("Successfully synced %d login records to CSV: %s", len(df), target_path)
        return str(target_path)
    except Exception as e:
        logger.error("Error syncing login records to CSV: %s", e)
        return ""


def get_login_records(limit: int = 100) -> List[Dict[str, Any]]:
    """Returns the most recent user login & registration records for admin audit."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, user_id, username, email, event_type, status, role, trading_style, ip_address, user_agent, details, created_at
                FROM user_login_records
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                created_val = d.get('created_at')
                if created_val:
                    try:
                        dt = datetime.fromisoformat(created_val.replace(" ", "T"))
                        dt_ist = dt + timedelta(hours=5, minutes=30)
                        d["timestamp_ist"] = dt_ist.strftime("%d-%b-%Y %I:%M:%S %p")
                    except Exception:
                        d["timestamp_ist"] = str(created_val)
                else:
                    d["timestamp_ist"] = "--"
                results.append(d)
            return results
        except Exception as e:
            logger.error("Error fetching login records: %s", e)
            return []
        finally:
            conn.close()


def generate_and_send_otp(phone: str, purpose: str = "register") -> Tuple[bool, str, Optional[str]]:
    return False, "OTP service has been disabled. Please register directly.", None

def verify_otp_and_login(phone: str, otp_code: str, ip_address: str = "127.0.0.1", user_agent: str = ""):
    return False, "OTP login disabled. Please log in with your username and password.", None, None

def verify_registration_otp(phone: str, otp_code: str) -> Tuple[bool, str]:
    return True, "Verified"


def sanitize_indian_phone(phone: str) -> Tuple[bool, str, str]:
    """
    Validates and standardizes a 10-digit Indian mobile number.
    Must start with 6, 7, 8, or 9.
    Returns: (is_valid: bool, clean_10_digits: str, error_message: str)
    """
    raw = re.sub(r"[^\d]", "", str(phone or "").strip())
    if raw.startswith("91") and len(raw) == 12:
        raw = raw[2:]
    elif raw.startswith("0") and len(raw) == 11:
        raw = raw[1:]

    if len(raw) != 10 or raw[0] not in "6789":
        return False, raw, "Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."
    return True, raw, ""


def check_phone_available(phone: str) -> Tuple[bool, str]:
    """
    Checks if an Indian mobile number is valid and not already registered.
    Returns: (is_available: bool, message: str)
    """
    valid, clean_phone, err = sanitize_indian_phone(phone)
    if not valid:
        return False, err

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE phone = ?", (clean_phone,))
            row = cursor.fetchone()
            if row:
                return False, f"Mobile number '+91 {clean_phone}' is already registered. Please Log In."
            return True, f"Mobile number '+91 {clean_phone}' is available for registration."
        except Exception as e:
            logger.error("Error checking phone availability: %s", e)
            return False, f"Database error checking phone: {e}"
        finally:
            conn.close()

def check_username_available(username: str) -> Tuple[bool, str]:
    """
    Checks if a username is valid and available for registration.
    Returns: (is_available: bool, message: str)
    """
    u = (username or "").strip().lower()
    if len(u) < 3:
        return False, "Username must be at least 3 characters long."
    if len(u) > 30:
        return False, "Username cannot exceed 30 characters."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", u):
        return False, "Username can only contain letters, numbers, hyphens, dots, and underscores."

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = ?", (u,))
            row = cursor.fetchone()
            if row:
                return False, f"Username '{u}' is already taken."
            return True, f"Username '{u}' is available."
        except Exception as e:
            logger.error("Error checking username availability: %s", e)
            return False, f"Database error checking username: {e}"
        finally:
            conn.close()

def register_user(username: str, email: str, password: str, trading_style: str = "intraday_scalper", accepted_policy: bool = True, ip_address: str = "127.0.0.1", user_agent: str = "", phone: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registers a new user.
    Returns: (success: bool, message: str, user_dict_or_none)
    """
    username = (username or "").strip().lower()
    email = (email or "").strip().lower()

    # Validate username format & availability
    avail, u_err = check_username_available(username)
    if not avail:
        return False, u_err, None

    if len(password) < 6:
        return False, "Password must be at least 6 characters long", None

    DISALLOWED_WEAK_PASSWORDS = {
        "123456", "12345678", "123456789", "password", "password123",
        "123@qweasd", "123qweasd", "admin123", "qwerty", "qwerty123",
        "iloveyou", "welcome", "welcome123", "123123", "111111",
        "abc123", "pass@123", "test1234", "admin@123", "admin2026",
        "qweasd123", "1234567890", "password1"
    }
    if password.strip().lower() in DISALLOWED_WEAK_PASSWORDS:
        return False, "This password was found in public internet breach lists. Please choose a stronger, unique password to prevent browser security warnings.", None

    if "@" not in email or "." not in email:
        return False, "Invalid email address format", None

    user_id = f"usr_{int(time.time())}_{os.urandom(3).hex()}"
    pw_hash = hash_password(password)

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check existing username or email
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False, f"Username '{username}' is already taken.", None

            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return False, f"Email address '{email}' is already registered.", None

            clean_phone = ""
            if phone:
                p_ok, clean_p, p_err = sanitize_indian_phone(phone)
                if not p_ok:
                    return False, p_err, None
                clean_phone = clean_p
                cursor.execute("SELECT id FROM users WHERE phone = ?", (clean_phone,))
                if cursor.fetchone():
                    return False, f"Mobile number '+91 {clean_phone}' is already registered to another account.", None
            else:
                return False, "Indian mobile number is required to register.", None

            cursor.execute(
                """
                INSERT INTO users (id, username, email, phone, password_hash, role, trading_style, accepted_policy, policy_accepted_at, policy_version, accepted_ip)
                VALUES (?, ?, ?, ?, ?, 'trader', ?, ?, CURRENT_TIMESTAMP, 'v2.0_sebi_full', ?)
                """,
                (user_id, username, email, clean_phone, pw_hash, trading_style, 1 if accepted_policy else 0, ip_address)
            )
            conn.commit()

            # Automatically export/sync all users to registered_users.csv
            try:
                sync_users_to_csv()
            except Exception as e_csv:
                logger.warning("Auto-sync users to CSV note: %s", e_csv)

            user_data = {
                "id": user_id,
                "username": username,
                "email": email,
                "phone": clean_phone,
                "role": "trader",
                "trading_style": trading_style,
            }
            # Live record new account creation in audit log and CSV
            try:
                record_login_activity(
                    user_id=user_id,
                    username=username,
                    email=email,
                    phone=clean_phone,
                    event_type="ACCOUNT_CREATED",
                    status="SUCCESS",
                    role="trader",
                    trading_style=trading_style,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details="New account created and SEBI legal disclaimer accepted"
                )
            except Exception as e_rec:
                logger.warning("Record account creation note: %s", e_rec)

            logger.info("Registered new user: %s (%s)", username, user_id)
            return True, "Registration successful", user_data
        except sqlite3.IntegrityError:
            return False, "Username or email already exists", None
        except Exception as e:
            logger.error("Error registering user: %s", e)
            return False, f"Server database error: {e}", None
        finally:
            conn.close()


def authenticate_user(login_identifier: str, password: str, ip_address: str = "127.0.0.1", user_agent: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]], Optional[str]]:
    """
    Authenticates user by username or email.
    Returns: (success: bool, message: str, user_dict_or_none, jwt_token_or_none)
    """
    identifier = login_identifier.strip().lower()

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, username, email, phone, password_hash, role, trading_style, is_frozen, freeze_reason FROM users WHERE username = ? OR email = ? OR phone = ?",
                (identifier, identifier, identifier)
            )
            row = cursor.fetchone()
            if not row:
                try:
                    record_login_activity(
                        user_id="",
                        username=identifier,
                        email="",
                        event_type="LOGIN_FAILED",
                        status="FAILED",
                        role="unknown",
                        trading_style="",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details="Failed login attempt: Username/email not found"
                    )
                except Exception:
                    pass
                return False, "Invalid username/email or password", None, None

            if not verify_password(password, row["password_hash"]):
                try:
                    record_login_activity(
                        user_id=row["id"],
                        username=row["username"],
                        email=row["email"],
                        event_type="LOGIN_FAILED",
                        status="FAILED",
                        role=row["role"],
                        trading_style=row["trading_style"],
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details="Failed login attempt: Incorrect password"
                    )
                except Exception:
                    pass
                return False, "Invalid username/email or password", None, None

            # Check if user account is frozen / suspended
            if row["is_frozen"]:
                reason = row["freeze_reason"] or "Irregular activity, bad requests, or misuse of this website"
                block_msg = f"Account Blocked: Your account has been suspended for {reason}. To unblock, contact developer at bodrarushit@gmail.com"
                try:
                    record_login_activity(
                        user_id=row["id"],
                        username=row["username"],
                        email=row["email"],
                        event_type="LOGIN_BLOCKED",
                        status="BLOCKED",
                        role=row["role"],
                        trading_style=row["trading_style"],
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details=block_msg
                    )
                except Exception:
                    pass
                return False, block_msg, None, None

            # Update last_login
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
            conn.commit()
            try:
                threading.Thread(target=sync_users_to_csv, daemon=True).start()
            except Exception:
                pass

            user_data = {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "phone": str(row["phone"] or ""),
                "role": row["role"],
                "trading_style": row["trading_style"],
            }
            token = create_access_token(row["id"], row["username"], row["role"], row["trading_style"])
            # Live record successful login in audit log and CSV
            try:
                record_login_activity(
                    user_id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    phone=str(row["phone"] or ""),
                    event_type="LOGIN_SUCCESS",
                    status="SUCCESS",
                    role=row["role"],
                    trading_style=row["trading_style"],
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details="User successfully authenticated via password"
                )
            except Exception as e_rec:
                logger.warning("Record login activity note: %s", e_rec)

            return True, "Login successful", user_data, token
        except Exception as e:
            logger.error("Authentication error: %s", e)
            return False, f"Server authentication error: {e}", None, None
        finally:
            conn.close()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetches user details by user_id."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, username, email, role, trading_style, created_at, last_login FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()


def get_all_users() -> List[Dict[str, Any]]:
    """Admin function: returns list of all registered users with drawings count."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT u.id, u.username, u.email, u.role, u.trading_style, u.created_at, u.last_login,
                   COUNT(d.id) as drawings_count
            FROM users u
            LEFT JOIN user_drawings d ON u.id = d.user_id
            GROUP BY u.id
            ORDER BY u.created_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def admin_reset_user_password(admin_key: str, target_user: str, new_password: str) -> Tuple[bool, str]:
    """
    Admin function: Resets any user's password using master secret key or admin role.
    target_user can be user_id, username, or email.
    """
    if admin_key != ADMIN_MASTER_KEY:
        return False, "Unauthorized: Invalid Master Admin Key"

    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long"

    target = target_user.strip().lower()
    pw_hash = hash_password(new_password)

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ? OR username = ? OR email = ?",
                (pw_hash, target_user, target, target)
            )
            if cursor.rowcount > 0:
                conn.commit()
                logger.info("Admin reset password for user: %s", target_user)
                return True, f"Password successfully reset for '{target_user}'"
            return False, f"User '{target_user}' not found"
        except Exception as e:
            logger.error("Error in admin_reset_user_password: %s", e)
            return False, f"Database error: {e}"
        finally:
            conn.close()


# --- User Drawings Management (Isolated per user) ---

def save_user_drawings(user_id: str, drawings: List[Dict[str, Any]]) -> Tuple[bool, str, int]:
    """
    Saves a user's full list of drawings atomically:
    - Replaces previous drawings for this user_id in SQLite.
    - Returns count of saved drawings.
    """
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM user_drawings WHERE user_id = ?", (user_id,))

            count = 0
            for d in drawings:
                did = str(d.get("id", f"draw_{int(time.time()*1000)}_{count}"))
                dtype = str(d.get("type", "line"))
                p1 = float(d.get("price1", 0.0) or 0.0)
                p2 = float(d.get("price2", p1) or p1)
                remark = str(d.get("remark", ""))
                payload = json.dumps(d)
                record_id = f"{user_id}_{did}"

                cursor.execute("""
                INSERT INTO user_drawings (id, user_id, drawing_id, drawing_type, price1, price2, remark, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (record_id, user_id, did, dtype, p1, p2, remark, payload))
                count += 1

            conn.commit()
            return True, "Drawings saved successfully", count
        except Exception as e:
            logger.error("Error saving user drawings: %s", e)
            return False, f"Database error: {e}", 0
        finally:
            conn.close()


def get_user_drawings(user_id: str) -> List[Dict[str, Any]]:
    """Loads all drawings belonging to a specific user_id."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT payload FROM user_drawings WHERE user_id = ? ORDER BY created_at ASC", (user_id,))
            rows = cursor.fetchall()
            drawings = []
            for r in rows:
                try:
                    drawings.append(json.loads(r["payload"]))
                except Exception:
                    pass
            return drawings
        finally:
            conn.close()


def delete_single_user_drawing(user_id: str, drawing_id: str) -> bool:
    """Deletes a specific drawing for a user."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            record_id = f"{user_id}_{drawing_id}"
            cursor.execute("DELETE FROM user_drawings WHERE id = ? OR (user_id = ? AND drawing_id = ?)", (record_id, user_id, drawing_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def clear_all_user_drawings(user_id: str) -> bool:
    """Wipes all drawings for a specific user."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM user_drawings WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()


# --- User Chat History Management ---

def save_user_chat_message(user_id: str, role: str, message: str):
    """Appends a message to the user's conversational memory."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?)",
                (user_id, role, message)
            )
            conn.commit()
        finally:
            conn.close()


def get_user_chat_history(user_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """Fetches recent chat messages for conversational context."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT role, message FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            messages = [{"role": r["role"], "message": r["message"]} for r in reversed(rows)]
            return messages
        finally:
            conn.close()


def clear_user_chat_history(user_id: str) -> bool:
    """Clears conversational history for a user."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()


def record_policy_acceptance(user_id: str, ip_address: str = "127.0.0.1") -> bool:
    """Updates user record with immutable legal policy acceptance timestamp and client IP."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE users
                SET accepted_policy = 1,
                    policy_accepted_at = CURRENT_TIMESTAMP,
                    policy_version = 'v2.0_sebi_full',
                    accepted_ip = ?
                WHERE id = ?
                """,
                (ip_address, user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Error recording policy acceptance: %s", e)
            return False
        finally:
            conn.close()


# --- User Preferences & Indicator State Management ---

def save_user_preferences(user_id: str, prefs: dict) -> bool:
    """Saves or updates custom indicator toggles, options, and preferences for a user."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_preferences (user_id, active_indicators, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    active_indicators = excluded.active_indicators,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, json.dumps(prefs))
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error("Error saving user preferences: %s", e)
            return False
        finally:
            conn.close()


def get_user_preferences(user_id: str) -> dict:
    """Loads saved indicator toggles and options for a specific user. Returns None if no data found."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT active_indicators FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row["active_indicators"]:
                try:
                    return json.loads(row["active_indicators"])
                except Exception:
                    return None
            return None
        finally:
            conn.close()


# --- Dedicated Per-User Copilot Tables & Central Review System ---

def _sanitize_table_username(username: str) -> str:
    """Sanitizes username for safe use in dedicated SQLite table names."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', (username or "guest").strip().lower())
    if not clean or clean[0].isdigit():
        clean = f"u_{clean}"
    return clean[:40]


def cleanup_expired_guest_chats(retention_days: int = 15) -> int:
    """
    Cleans up temporary guest chats older than retention_days (15 days).
    Registered user chats remain permanently stored.
    Returns: total rows deleted across guest tables.
    """
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        total_deleted = 0
        try:
            cutoff_clause = f"-{int(retention_days)} days"

            # 1. Prune temporary guest table (copilot_user_guest)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='copilot_user_guest'")
            if cursor.fetchone():
                cursor.execute(
                    "DELETE FROM copilot_user_guest WHERE created_at < datetime('now', ?)",
                    (cutoff_clause,)
                )
                total_deleted += cursor.rowcount

            # 2. Prune guest records from central review table
            cursor.execute("""
            DELETE FROM copilot_queries_review
            WHERE (LOWER(username) = 'guest' OR LOWER(user_id) LIKE 'guest%')
              AND created_at < datetime('now', ?)
            """, (cutoff_clause,))
            total_deleted += cursor.rowcount

            # 3. Prune guest records from conversational memory table
            cursor.execute("""
            DELETE FROM chat_history
            WHERE (LOWER(user_id) = 'guest' OR LOWER(user_id) LIKE 'guest%')
              AND created_at < datetime('now', ?)
            """, (cutoff_clause,))
            total_deleted += cursor.rowcount

            conn.commit()
            if total_deleted > 0:
                logger.info("Cleaned up %d temporary guest chat rows older than %d days.", total_deleted, retention_days)
            return total_deleted
        except Exception as e:
            logger.error("Error cleaning up expired guest chats: %s", e)
            return 0
        finally:
            conn.close()


def save_copilot_query_record(
    user_id: str,
    username: str,
    query: str,
    response: str,
    intent: str = "general",
    market_price: float = 0.0,
    timeframe: str = "5m",
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Saves a user's question and Copilot's response:
    1. Into a dedicated table for that specific user: copilot_user_<username>
    2. Into the master review table: copilot_queries_review (for admin review)
    Returns: the review record ID.
    """
    safe_uname = _sanitize_table_username(username)
    user_table_name = f"copilot_user_{safe_uname}"

    # Temporary storage rule: Guest chats stored for max 15 days; prune expired records
    is_guest_query = (username or "").strip().lower() == "guest" or (user_id or "").strip().lower().startswith("guest")
    if is_guest_query:
        try:
            cleanup_expired_guest_chats(retention_days=15)
        except Exception:
            pass
    meta_str = json.dumps(metadata or {})

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. Ensure user-specific dedicated table exists
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {user_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                intent TEXT,
                market_price REAL,
                timeframe TEXT DEFAULT '5m',
                hidden_from_user INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            );
            """)

            # Ensure hidden_from_user exists in case table was created earlier
            cursor.execute(f"PRAGMA table_info({user_table_name})")
            t_cols = [r["name"] for r in cursor.fetchall()]
            if "hidden_from_user" not in t_cols:
                cursor.execute(f"ALTER TABLE {user_table_name} ADD COLUMN hidden_from_user INTEGER DEFAULT 0")

            # 2. Insert into user-specific table
            cursor.execute(f"""
            INSERT INTO {user_table_name} (user_id, username, query, response, intent, market_price, timeframe, hidden_from_user, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (user_id, username, query, response, intent, market_price, timeframe, meta_str))

            # 3. Insert into central review table
            cursor.execute("""
            INSERT INTO copilot_queries_review (
                user_id, username, user_table, query, response, intent, market_price, timeframe, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, user_table_name, query, response, intent, market_price, timeframe, meta_str))

            review_id = cursor.lastrowid
            conn.commit()
            logger.info("Saved Copilot query for user '%s' in table '%s' and review id %s", username, user_table_name, review_id)
            return review_id
        except Exception as e:
            logger.error("Error saving Copilot query record: %s", e)
            return 0
        finally:
            conn.close()


def get_copilot_queries_for_review(
    status: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Admin function: fetches queries from copilot_queries_review for inspection/audit.
    Supports filtering by review_status ('pending', 'reviewed', 'flagged') and username.
    """
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM copilot_queries_review WHERE 1=1"
            params: List[Any] = []

            if status and status.lower() != "all":
                query += " AND review_status = ?"
                params.append(status.lower())

            if username:
                query += " AND (username = ? OR user_id = ?)"
                params.extend([username, username])

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([max(1, min(limit, 200)), max(0, offset)])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("metadata"):
                    try:
                        item["metadata"] = json.loads(item["metadata"])
                    except Exception:
                        pass
                results.append(item)
            return results
        finally:
            conn.close()


def sync_copilot_queries_to_csv(csv_path: Optional[Path] = None) -> str:
    """
    Exports all copilot queries and responses from copilot_queries_review into copilot_chat_queries.csv.
    Stores in both project root and database/ folder.
    """
    try:
        import pandas as pd
        with _db_lock:
            conn = get_db_connection()
            query = """
                SELECT id, user_id, username, query, response, intent, market_price, timeframe, review_status, admin_notes, metadata, created_at
                FROM copilot_queries_review
                ORDER BY created_at DESC
            """
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

        target_path = csv_path or COPILOT_QUERIES_CSV_PATH
        if not rows:
            df_empty = pd.DataFrame(columns=COPILOT_CSV_COLUMNS)
            df_empty.to_csv(str(target_path), index=False, encoding='utf-8-sig')
            if COPILOT_QUERIES_CSV_BACKUP_PATH != target_path:
                df_empty.to_csv(str(COPILOT_QUERIES_CSV_BACKUP_PATH), index=False, encoding='utf-8-sig')
            return str(target_path)

        data = []
        for r in rows:
            d = dict(r)
            created_val = d.get('created_at')
            if created_val:
                try:
                    dt = pd.to_datetime(created_val)
                    dt_ist = dt + timedelta(hours=5, minutes=30)
                    ist_str = dt_ist.strftime('%d-%b-%Y %I:%M:%S %p')
                except Exception:
                    ist_str = str(created_val)
            else:
                ist_str = '--'

            meta = {}
            if d.get("metadata"):
                try:
                    meta = json.loads(d["metadata"]) if isinstance(d["metadata"], str) else d["metadata"]
                except Exception:
                    meta = {}

            data.append({
                "Query ID": d.get("id"),
                "Timestamp (IST)": ist_str,
                "Username": d.get("username", "Guest"),
                "User ID": d.get("user_id", ""),
                "User Query": d.get("query", ""),
                "AI Copilot Response": d.get("response", ""),
                "Intent": d.get("intent", ""),
                "Market Price": d.get("market_price", ""),
                "Timeframe": d.get("timeframe", "5m"),
                "Review Status": d.get("review_status", "pending"),
                "Admin Notes": d.get("admin_notes", ""),
                "Trading Style": meta.get("trading_style", ""),
                "Confluence": meta.get("confluence", ""),
                "Client IP": meta.get("client_ip", "")
            })

        df = pd.DataFrame(data, columns=COPILOT_CSV_COLUMNS)
        df.to_csv(str(target_path), index=False, encoding='utf-8-sig')
        if COPILOT_QUERIES_CSV_BACKUP_PATH != target_path:
            df.to_csv(str(COPILOT_QUERIES_CSV_BACKUP_PATH), index=False, encoding='utf-8-sig')
        logger.info("Successfully synced %d copilot query records to %s", len(df), target_path)
        return str(target_path)
    except Exception as e:
        logger.error("Error syncing copilot queries to CSV: %s", e)
        return str(csv_path or COPILOT_QUERIES_CSV_PATH)


def update_copilot_query_review(query_id: int, review_status: str, admin_notes: str = "") -> bool:
    """Admin function: updates review status and notes for a copilot query."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            UPDATE copilot_queries_review
            SET review_status = ?, admin_notes = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (review_status.lower(), admin_notes, query_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error("Error updating copilot review status: %s", e)
            return False
        finally:
            conn.close()


def get_user_own_copilot_queries(username: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches a user's own query history directly from their dedicated user table."""
    safe_uname = _sanitize_table_username(username)
    user_table_name = f"copilot_user_{safe_uname}"

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (user_table_name,))
            if not cursor.fetchone():
                return []

            cursor.execute(f"SELECT * FROM {user_table_name} ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("Error fetching user copilot queries from %s: %s", user_table_name, e)
            return []
        finally:
            conn.close()


def get_user_copilot_display_history(username: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetches lifetime conversation history visible to the user (where hidden_from_user == 0).
    Sorted in chronological order (created_at ASC) for continuous chat thread display.
    If the user has not clicked 'Clear Chat', all lifetime messages are shown.
    """
    safe_uname = _sanitize_table_username(username)
    user_table_name = f"copilot_user_{safe_uname}"

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (user_table_name,))
            if not cursor.fetchone():
                return []

            # Check if hidden_from_user column exists
            cursor.execute(f"PRAGMA table_info({user_table_name})")
            cols = [r["name"] for r in cursor.fetchall()]
            if "hidden_from_user" in cols:
                cursor.execute(f"""
                    SELECT id, user_id, username, query, response, intent, market_price, timeframe, created_at, metadata
                    FROM {user_table_name}
                    WHERE hidden_from_user = 0
                    ORDER BY id ASC
                    LIMIT ?
                """, (max(1, min(limit, 5000)),))
            else:
                cursor.execute(f"""
                    SELECT id, user_id, username, query, response, intent, market_price, timeframe, created_at, metadata
                    FROM {user_table_name}
                    ORDER BY id ASC
                    LIMIT ?
                """, (max(1, min(limit, 5000)),))

            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("Error fetching copilot display history from %s: %s", user_table_name, e)
            return []
        finally:
            conn.close()


def soft_clear_user_copilot_history(username: str, user_id: str = None) -> bool:
    """
    User clicks 'Clear Chat':
    Soft-clears the conversation from the user's screen by setting hidden_from_user = 1.
    CRUCIAL: No records are EVER deleted from the database!
    100% of all queries and answers remain permanently preserved in:
    1. copilot_user_<username> (dedicated user table)
    2. copilot_queries_review (consolidated developer/admin audit table)
    """
    safe_uname = _sanitize_table_username(username)
    user_table_name = f"copilot_user_{safe_uname}"

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (user_table_name,))
            if not cursor.fetchone():
                return True

            # Ensure hidden_from_user column exists
            cursor.execute(f"PRAGMA table_info({user_table_name})")
            cols = [r["name"] for r in cursor.fetchall()]
            if "hidden_from_user" not in cols:
                cursor.execute(f"ALTER TABLE {user_table_name} ADD COLUMN hidden_from_user INTEGER DEFAULT 0")

            # Soft-delete for user view: update hidden_from_user to 1
            cursor.execute(f"UPDATE {user_table_name} SET hidden_from_user = 1 WHERE hidden_from_user = 0")

            # In the central review table, mark user_cleared_display = 1 (DO NOT DELETE)
            try:
                cursor.execute("PRAGMA table_info(copilot_queries_review)")
                r_cols = [r["name"] for r in cursor.fetchall()]
                if "user_cleared_display" not in r_cols:
                    cursor.execute("ALTER TABLE copilot_queries_review ADD COLUMN user_cleared_display INTEGER DEFAULT 0")
                if user_id:
                    cursor.execute("UPDATE copilot_queries_review SET user_cleared_display = 1 WHERE user_id = ? OR username = ?", (user_id, username))
                else:
                    cursor.execute("UPDATE copilot_queries_review SET user_cleared_display = 1 WHERE username = ?", (username,))
            except Exception as e_rev:
                logger.debug("Non-fatal note updating review table flag: %s", e_rev)

            conn.commit()
            logger.info("Soft-cleared Copilot chat for user '%s'. All database rows permanently retained.", username)
            return True
        except Exception as e:
            logger.error("Error soft-clearing copilot history for %s: %s", username, e)
            return False
        finally:
            conn.close()


def get_all_copilot_user_tables() -> List[str]:
    """Returns list of all dedicated per-user copilot tables present in the database."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'copilot_user_%' ORDER BY name ASC")
            rows = cursor.fetchall()
            return [r["name"] for r in rows]
        finally:
            conn.close()


# --- Trade Predictions & Learning Journal Methods ---

def save_prediction(pred_data: Dict[str, Any]) -> str:
    """Inserts a new prediction into the common database."""
    pred_id = pred_data.get("id") or f"pred_{int(time.time() * 1000)}"
    user_id = pred_data.get("user_id")
    username = pred_data.get("username", "Trader")
    source = pred_data.get("source", "MANUAL")
    symbol = pred_data.get("symbol", "NIFTY 50")
    timeframe = pred_data.get("timeframe", "5m")
    direction = str(pred_data.get("direction", "BUY")).upper()
    entry = float(pred_data.get("entry_price", 0.0))
    target = float(pred_data.get("target_price", 0.0))
    stop = float(pred_data.get("stop_loss", 0.0))

    target_diff = abs(target - entry)
    stop_diff = abs(entry - stop)
    rr = round(target_diff / stop_diff, 2) if stop_diff > 0 else 1.0

    predicted_pts = round(target - entry if direction in ("BUY", "CALL", "LONG") else entry - target, 2)
    predicted_pct = round((predicted_pts / entry) * 100, 2) if entry > 0 else 0.0

    market_context = pred_data.get("market_context")
    if isinstance(market_context, dict):
        market_context_str = json.dumps(market_context)
    else:
        market_context_str = str(market_context or "{}")

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO trade_predictions (
                id, user_id, username, source, symbol, timeframe, direction,
                entry_price, target_price, stop_loss, rr_ratio,
                predicted_pnl_pts, predicted_pnl_pct, status, market_context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """, (
                pred_id, user_id, username, source, symbol, timeframe, direction,
                entry, target, stop, rr, predicted_pts, predicted_pct, market_context_str
            ))
            conn.commit()
            logger.info("Saved prediction %s (%s %s @ ₹%.2f) to database.", pred_id, source, direction, entry)
            return pred_id
        finally:
            conn.close()


def update_prediction(pred_id: str, updates: Dict[str, Any]) -> bool:
    """Updates fields of an existing prediction in the database."""
    if not updates:
        return False

    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            fields = []
            vals = []
            for k, v in updates.items():
                if k == "market_context" and isinstance(v, dict):
                    v = json.dumps(v)
                fields.append(f"{k} = ?")
                vals.append(v)
            vals.append(pred_id)

            sql = f"UPDATE trade_predictions SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(sql, vals)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def get_active_predictions(limit: int = 200) -> List[Dict[str, Any]]:
    """Retrieves all currently active predictions."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM trade_predictions WHERE status = 'ACTIVE' ORDER BY created_at ASC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_prediction_by_id(pred_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves single prediction by ID."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM trade_predictions WHERE id = ?", (pred_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_all_predictions(user_id: Optional[str] = None, source: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieves predictions filtered optionally by user or source."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM trade_predictions"
            params = []
            conditions = []
            if user_id:
                conditions.append("(user_id = ? OR user_id IS NULL OR source IN ('MAIN_STRATEGY', 'SR_BREAKOUT', 'SR_REVERSAL', 'RAG_COPILOT'))")
                params.append(user_id)
            if source:
                conditions.append("source = ?")
                params.append(source)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_prediction_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Computes comprehensive prediction accuracy, win rate, and error analytics."""
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            where_clause = ""
            params = []
            if user_id:
                where_clause = "WHERE (user_id = ? OR source IN ('MAIN_STRATEGY', 'SR_BREAKOUT', 'SR_REVERSAL', 'RAG_COPILOT'))"
                params = [user_id]

            cursor.execute(f"SELECT COUNT(*) as total FROM trade_predictions {where_clause}", params)
            total = cursor.fetchone()["total"]

            cursor.execute(f"SELECT COUNT(*) as active FROM trade_predictions WHERE status = 'ACTIVE' {'AND (' + where_clause[6:] + ')' if where_clause else ''}", params)
            active = cursor.fetchone()["active"]

            cursor.execute(f"SELECT COUNT(*) as wins FROM trade_predictions WHERE status = 'TARGET_HIT' {'AND (' + where_clause[6:] + ')' if where_clause else ''}", params)
            target_hits = cursor.fetchone()["wins"]

            cursor.execute(f"SELECT COUNT(*) as losses FROM trade_predictions WHERE status = 'SL_HIT' {'AND (' + where_clause[6:] + ')' if where_clause else ''}", params)
            sl_hits = cursor.fetchone()["losses"]

            resolved = target_hits + sl_hits
            win_rate = round((target_hits / resolved) * 100, 1) if resolved > 0 else 0.0

            cursor.execute(f"""
            SELECT 
                AVG(predicted_pnl_pts) as avg_pred,
                AVG(actual_pnl_pts) as avg_actual,
                AVG(ABS(pnl_error_pts)) as avg_error,
                SUM(actual_pnl_pts) as net_pts
            FROM trade_predictions
            WHERE status IN ('TARGET_HIT', 'SL_HIT') {'AND (' + where_clause[6:] + ')' if where_clause else ''}
            """, params)
            pnl_row = cursor.fetchone()

            avg_pred = round(pnl_row["avg_pred"] or 0.0, 2)
            avg_actual = round(pnl_row["avg_actual"] or 0.0, 2)
            avg_error = round(pnl_row["avg_error"] or 0.0, 2)
            net_pts = round(pnl_row["net_pts"] or 0.0, 2)

            # Error category breakdown
            cursor.execute(f"""
            SELECT error_category, COUNT(*) as count 
            FROM trade_predictions 
            WHERE status = 'SL_HIT' AND error_category IS NOT NULL {'AND (' + where_clause[6:] + ')' if where_clause else ''}
            GROUP BY error_category ORDER BY count DESC
            """, params)
            err_rows = cursor.fetchall()
            error_breakdown = {r["error_category"]: r["count"] for r in err_rows}

            # Source breakdown
            cursor.execute(f"""
            SELECT source, COUNT(*) as count 
            FROM trade_predictions {where_clause}
            GROUP BY source ORDER BY count DESC
            """, params)
            src_rows = cursor.fetchall()
            source_breakdown = {r["source"]: r["count"] for r in src_rows}

            return {
                "total_predictions": total,
                "active_predictions": active,
                "resolved_predictions": resolved,
                "target_hit_count": target_hits,
                "sl_hit_count": sl_hits,
                "win_rate_pct": win_rate,
                "avg_predicted_pnl_pts": avg_pred,
                "avg_actual_pnl_pts": avg_actual,
                "avg_pnl_error_pts": avg_error,
                "net_actual_pnl_pts": net_pts,
                "error_breakdown": error_breakdown,
                "source_breakdown": source_breakdown,
            }
        finally:
            conn.close()


def get_user_psychology_profile(user_id: str) -> Dict[str, Any]:
    """Retrieves user behavioral and psychological profile or initializes default."""
    if not user_id:
        return {
            "discipline_score": 85,
            "emotional_state": "Disciplined",
            "overtrading_count": 0,
            "lunch_chop_trades": 0,
            "weaknesses": ["Chasing entries near ±2σ bands", "Trading during 11:30–13:15 Lunch Chop"],
            "strengths": ["Respects 1 Lot = 65 quantity rule", "Patient on Morning Prime breakouts"],
            "coaching_summary": "Maintain strict patience during lunch consolidation. Focus only on >5x touch S&R confluences."
        }
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
                u_row = cursor.fetchone()
                uname = u_row["username"] if u_row else "Trader"
                default_weaknesses = json.dumps(["Taking breakouts during Lunch Chop (11:30–13:15)", "Impatience at ±2σ exhaustion bands"])
                default_strengths = json.dumps(["Strictly adheres to 1 Lot (65 qty) sizing", "Waits for 5m candle confirmation"])
                cursor.execute("""
                    INSERT INTO user_psychology_profile 
                    (user_id, username, discipline_score, emotional_state, weaknesses, strengths, coaching_summary)
                    VALUES (?, ?, 85, 'Disciplined', ?, ?, 'Prioritize Morning Prime (09:30–11:30) and Afternoon (13:15–14:45) windows. Avoid Lunch Chop.')
                """, (user_id, uname, default_weaknesses, default_strengths))
                conn.commit()
                cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "discipline_score": row["discipline_score"],
                "risk_tolerance": row["risk_tolerance"],
                "emotional_state": row["emotional_state"],
                "overtrading_count": row["overtrading_count"],
                "revenge_trading_count": row["revenge_trading_count"],
                "lunch_chop_trades": row["lunch_chop_trades"],
                "weaknesses": json.loads(row["weaknesses"] or "[]"),
                "strengths": json.loads(row["strengths"] or "[]"),
                "coaching_summary": row["coaching_summary"] or "",
                "updated_at": str(row["updated_at"]),
            }
        except Exception as e:
            logger.error("Error fetching user psychology profile: %s", e)
            return {"discipline_score": 85, "emotional_state": "Disciplined"}
        finally:
            conn.close()


def update_user_psychology_profile(user_id: str, updates: Dict[str, Any]) -> bool:
    """Updates fields of user psychology profile."""
    if not user_id:
        return False
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            allowed = {"discipline_score", "risk_tolerance", "emotional_state", "overtrading_count", "revenge_trading_count", "lunch_chop_trades", "weaknesses", "strengths", "coaching_summary"}
            fields = []
            vals = []
            for k, v in updates.items():
                if k in allowed:
                    fields.append(f"{k} = ?")
                    vals.append(json.dumps(v) if isinstance(v, (list, dict)) else v)
            if not fields:
                return False
            from datetime import datetime
            vals.append(datetime.utcnow().isoformat())
            vals.append(user_id)
            cursor.execute(f"UPDATE user_psychology_profile SET {', '.join(fields)}, updated_at = ? WHERE user_id = ?", vals)
            conn.commit()
            return True
        except Exception as e:
            logger.error("Error updating psychology profile: %s", e)
            return False
        finally:
            conn.close()


def record_user_psychology_event(user_id: str, event_type: str, details: str) -> bool:
    """Records a behavioral event (e.g. Lunch Chop violation or discipline adherence)."""
    if not user_id:
        return False
    with _db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            from datetime import datetime
            cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                get_user_psychology_profile(user_id)
                cursor.execute("SELECT * FROM user_psychology_profile WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

            score = int(row["discipline_score"] or 85)
            lc = int(row["lunch_chop_trades"] or 0)
            ot = int(row["overtrading_count"] or 0)
            rv = int(row["revenge_trading_count"] or 0)
            ev_list = json.loads(row["history_events"] or "[]")
            ev_list.append({"time": datetime.utcnow().isoformat(), "type": event_type, "details": details})
            ev_list = ev_list[-30:]

            if event_type == "LUNCH_CHOP_ENTRY":
                lc += 1
                score = max(30, score - 6)
            elif event_type == "REVENGE_TRADE":
                rv += 1
                score = max(20, score - 10)
            elif event_type == "OVERTRADING":
                ot += 1
                score = max(30, score - 5)
            elif event_type == "DISCIPLINE_FOLLOWED":
                score = min(100, score + 4)

            cursor.execute("""
                UPDATE user_psychology_profile 
                SET discipline_score = ?, lunch_chop_trades = ?, overtrading_count = ?, revenge_trading_count = ?, history_events = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (score, lc, ot, rv, json.dumps(ev_list), user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error("Error recording psychology event: %s", e)
            return False
        finally:
            conn.close()


init_database()


# ==============================================================
# 📊 Real-Time Visitor Analytics & Conversion Tracking
# ==============================================================

_IP_GEO_CACHE: Dict[str, Dict[str, str]] = {}
_IP_GEO_LOCK = threading.Lock()

def get_ip_geo_info(ip: str) -> Dict[str, str]:
    """
    Resolves IP Geolocation (City, State/Region, Country, ISP) with memory caching.
    Safely ignores private/localhost IPs.
    """
    clean_ip = (ip or "").strip()
    if not clean_ip or clean_ip in ("127.0.0.1", "localhost", "::1", "testclient") or clean_ip.startswith("192.168.") or clean_ip.startswith("10."):
        return {"city": "Localhost", "region": "Internal", "country": "Local", "isp": "Internal", "postal": ""}

    with _IP_GEO_LOCK:
        if clean_ip in _IP_GEO_CACHE:
            return _IP_GEO_CACHE[clean_ip]

    geo = {"city": "", "region": "", "country": "IN", "isp": "", "postal": ""}
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://ipinfo.io/{clean_ip}/json",
            headers={"User-Agent": "NIFTY-Terminal-Audit/1.0"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            geo["city"] = data.get("city") or ""
            geo["region"] = data.get("region") or ""
            geo["country"] = data.get("country") or "IN"
            geo["isp"] = data.get("org") or data.get("hostname") or ""
            geo["postal"] = data.get("postal") or ""
    except Exception as e:
        logger.debug("Geo lookup notice for %s: %s", clean_ip, e)

    with _IP_GEO_LOCK:
        _IP_GEO_CACHE[clean_ip] = geo

    return geo


def resolve_ip_geo_async(ip: str, visitor_id: str):
    """Asynchronously resolves IP geo and updates visitor_identities record."""
    def _worker():
        geo = get_ip_geo_info(ip)
        if geo.get("city") or geo.get("isp"):
            try:
                with _db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE visitor_identities
                        SET city = CASE WHEN (city IS NULL OR city = '' OR city = 'Unknown') THEN ? ELSE city END,
                            region = CASE WHEN (region IS NULL OR region = '') THEN ? ELSE region END,
                            country = CASE WHEN (country IS NULL OR country = '') THEN ? ELSE country END,
                            org_isp = CASE WHEN (org_isp IS NULL OR org_isp = '') THEN ? ELSE org_isp END
                        WHERE visitor_id = ?
                    """, (geo.get("city", ""), geo.get("region", ""), geo.get("country", ""), geo.get("isp", ""), visitor_id))
                    conn.commit()
                    conn.close()
            except Exception as ex:
                logger.debug("Async geo update note: %s", ex)

    threading.Thread(target=_worker, daemon=True).start()


def parse_user_agent_details(user_agent: str) -> Tuple[str, str, str]:
    """Returns (device_type, browser, os_name)."""
    ua = (user_agent or "").lower()

    # Device
    if any(k in ua for k in ["mobile", "android", "iphone", "ipod", "blackberry", "windows phone"]):
        device = "Mobile"
    elif "ipad" in ua or "tablet" in ua:
        device = "Tablet"
    else:
        device = "Desktop"

    # Browser
    if "edg/" in ua:
        browser = "Edge"
    elif "chrome" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "opera" in ua or "opr/" in ua:
        browser = "Opera"
    else:
        browser = "Chrome" if "chrome" in ua else "Other"

    # OS
    if "windows nt 10.0" in ua:
        os_name = "Windows 10/11"
    elif "windows nt" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        os_name = "iOS"
    elif "macintosh" in ua or "mac os x" in ua:
        os_name = "macOS"
    elif "cros" in ua:
        os_name = "ChromeOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Desktop" if device == "Desktop" else "Mobile"

    return device, browser, os_name


def record_visitor_action(
    visitor_id: str,
    action_type: str,
    action_detail: str = "",
    path: str = "/",
    ip: str = "",
    user_agent: str = "",
    user_id: Optional[str] = None
) -> bool:
    """
    Logs every user action (timeframe change, indicator toggle, news open, copilot, etc.)
    with IP, city, ISP, device, OS, and timestamp.
    """
    if not visitor_id or not visitor_id.strip():
        return False
    visitor_id = visitor_id.strip()
    device, browser, os_name = parse_user_agent_details(user_agent)
    geo = get_ip_geo_info(ip)
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            uname = "Guest"
            valid_user_id = None
            if user_id:
                cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
                urow = cursor.fetchone()
                if urow:
                    valid_user_id = urow["id"]
                    uname = urow["username"]

            cursor.execute("""
                INSERT INTO visitor_activity_log (
                    visitor_id, user_id, username, action_type, action_detail,
                    path, ip_address, city, region, country, isp,
                    device_type, os_name, browser, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                visitor_id, valid_user_id, uname, action_type, action_detail[:255],
                path[:100], ip, geo.get("city", ""), geo.get("region", ""),
                geo.get("country", ""), geo.get("isp", ""), device, os_name, browser, now_utc
            ))

            # Update visitor_identities last_seen, IP and location
            cursor.execute("""
                UPDATE visitor_identities
                SET last_seen = ?,
                    ip_address = CASE WHEN ? != '' THEN ? ELSE ip_address END,
                    city = CASE WHEN ? != '' AND (city IS NULL OR city = '' OR city = 'Unknown') THEN ? ELSE city END,
                    region = CASE WHEN ? != '' AND (region IS NULL OR region = '') THEN ? ELSE region END,
                    org_isp = CASE WHEN ? != '' AND (org_isp IS NULL OR org_isp = '') THEN ? ELSE org_isp END,
                    os_name = CASE WHEN ? != '' THEN ? ELSE os_name END
                WHERE visitor_id = ?
            """, (
                now_utc, ip, ip,
                geo.get("city", ""), geo.get("city", ""),
                geo.get("region", ""), geo.get("region", ""),
                geo.get("isp", ""), geo.get("isp", ""),
                os_name, os_name, visitor_id
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error("Error in record_visitor_action: %s", e)
            return False
        finally:
            conn.close()


def get_daily_visitor_summary(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Returns daily aggregated visitor activity summaries for the Admin Dashboard.
    Groups visits by date and visitor_id, computing total time active, total actions, and IP location.
    """
    import pandas as pd
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    DATE(a.created_at) as log_date,
                    a.visitor_id,
                    a.username,
                    a.user_id,
                    a.ip_address,
                    COALESCE(NULLIF(v.city, ''), a.city) as city,
                    COALESCE(NULLIF(v.region, ''), a.region) as region,
                    COALESCE(NULLIF(v.country, ''), a.country) as country,
                    COALESCE(NULLIF(v.org_isp, ''), a.isp) as isp,
                    a.device_type,
                    a.os_name,
                    a.browser,
                    MIN(a.created_at) as first_action_utc,
                    MAX(a.created_at) as last_action_utc,
                    COUNT(*) as total_actions,
                    GROUP_CONCAT(DISTINCT a.action_type) as action_types
                FROM visitor_activity_log a
                LEFT JOIN visitor_identities v ON a.visitor_id = v.visitor_id
                GROUP BY DATE(a.created_at), a.visitor_id
                ORDER BY MAX(a.created_at) DESC
                LIMIT ?
            """
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    f_dt = pd.to_datetime(d["first_action_utc"]) + timedelta(hours=5, minutes=30)
                    l_dt = pd.to_datetime(d["last_action_utc"]) + timedelta(hours=5, minutes=30)
                    d["first_action_ist"] = f_dt.strftime("%d-%b %I:%M %p")
                    d["last_action_ist"] = l_dt.strftime("%d-%b %I:%M %p")
                    diff_mins = max(1, int(round((l_dt - f_dt).total_seconds() / 60.0)))
                    d["active_minutes"] = diff_mins
                except Exception:
                    d["first_action_ist"] = str(d.get("first_action_utc", "--"))
                    d["last_action_ist"] = str(d.get("last_action_utc", "--"))
                    d["active_minutes"] = 1

                city = d.get("city") or ""
                region = d.get("region") or ""
                d["location_str"] = f"{city}, {region}" if city and region else (city or region or "India")
                results.append(d)
            return results
        finally:
            conn.close()


def sync_visitor_activity_to_csv(csv_path: Optional[Path] = None) -> str:
    """
    Exports all granular visitor activity logs into visitor_daily_activity.csv.
    """
    try:
        import pandas as pd
        with _db_lock:
            conn = get_db_connection()
            query = """
                SELECT id, created_at, visitor_id, username, action_type, action_detail,
                       ip_address, city, region, country, isp, device_type, os_name, browser, path
                FROM visitor_activity_log
                ORDER BY created_at DESC
            """
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

        target_path = csv_path or VISITOR_ACTIVITY_CSV_PATH
        if not rows:
            df_empty = pd.DataFrame(columns=VISITOR_ACTIVITY_CSV_COLUMNS)
            df_empty.to_csv(str(target_path), index=False, encoding='utf-8-sig')
            if VISITOR_ACTIVITY_CSV_BACKUP_PATH != target_path:
                df_empty.to_csv(str(VISITOR_ACTIVITY_CSV_BACKUP_PATH), index=False, encoding='utf-8-sig')
            return str(target_path)

        data = []
        for r in rows:
            d = dict(r)
            created_val = d.get('created_at')
            if created_val:
                try:
                    dt = pd.to_datetime(created_val) + timedelta(hours=5, minutes=30)
                    ist_str = dt.strftime('%d-%b-%Y %I:%M:%S %p')
                except Exception:
                    ist_str = str(created_val)
            else:
                ist_str = '--'

            data.append({
                "Activity ID": d.get("id"),
                "Timestamp (IST)": ist_str,
                "Visitor ID": d.get("visitor_id", ""),
                "Account / User": d.get("username", "Guest"),
                "Action": d.get("action_type", ""),
                "Action Details": d.get("action_detail", ""),
                "IP Address": d.get("ip_address", ""),
                "City": d.get("city", ""),
                "State / Region": d.get("region", ""),
                "Country": d.get("country", "IN"),
                "ISP / Network": d.get("isp", ""),
                "Device": d.get("device_type", "Desktop"),
                "OS": d.get("os_name", ""),
                "Browser": d.get("browser", ""),
                "Page Path": d.get("path", "/")
            })

        df = pd.DataFrame(data, columns=VISITOR_ACTIVITY_CSV_COLUMNS)
        df.to_csv(str(target_path), index=False, encoding='utf-8-sig')
        if VISITOR_ACTIVITY_CSV_BACKUP_PATH != target_path:
            df.to_csv(str(VISITOR_ACTIVITY_CSV_BACKUP_PATH), index=False, encoding='utf-8-sig')
        logger.info("Successfully synced %d visitor activity logs to %s", len(df), target_path)
        return str(target_path)
    except Exception as e:
        logger.error("Error syncing visitor activity to CSV: %s", e)
        return str(csv_path or VISITOR_ACTIVITY_CSV_PATH)


def record_visitor_hit(
    visitor_id: str,
    ip: str = "",
    user_agent: str = "",
    path: str = "/",
    referrer: str = "",
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ingests a visitor pageview beacon.
    Creates or updates the visitor identity and records the granular pageview.
    """
    if not visitor_id or not visitor_id.strip():
        return {"status": "error", "message": "visitor_id required"}

    visitor_id = visitor_id.strip()
    device_type, browser, os_name = parse_user_agent_details(user_agent)
    geo = get_ip_geo_info(ip)
    if ip and (not geo.get("city") or geo.get("city") == "Unknown"):
        resolve_ip_geo_async(ip, visitor_id)

    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Verify if user_id exists in users table to prevent FK errors
            valid_user_id = None
            if user_id:
                cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                if cursor.fetchone():
                    valid_user_id = user_id

            has_acc = 1 if valid_user_id else 0

            # Check if visitor exists
            cursor.execute("SELECT visitor_id, has_account, user_id FROM visitor_identities WHERE visitor_id = ?", (visitor_id,))
            row = cursor.fetchone()

            if row:
                new_has_acc = 1 if (row["has_account"] or valid_user_id) else 0
                new_user_id = valid_user_id if valid_user_id else row["user_id"]
                cursor.execute("""
                    UPDATE visitor_identities 
                    SET last_seen = ?, 
                        visit_count = visit_count + 1, 
                        has_account = ?, 
                        user_id = ?,
                        ip_address = CASE WHEN ? != '' THEN ? ELSE ip_address END,
                        city = CASE WHEN ? != '' AND (city IS NULL OR city = '' OR city = 'Unknown') THEN ? ELSE city END,
                        region = CASE WHEN ? != '' AND (region IS NULL OR region = '') THEN ? ELSE region END,
                        org_isp = CASE WHEN ? != '' AND (org_isp IS NULL OR org_isp = '') THEN ? ELSE org_isp END,
                        os_name = CASE WHEN ? != '' THEN ? ELSE os_name END
                    WHERE visitor_id = ?
                """, (now_utc, new_has_acc, new_user_id, ip, ip, geo.get("city", ""), geo.get("city", ""), geo.get("region", ""), geo.get("region", ""), geo.get("isp", ""), geo.get("isp", ""), os_name, os_name, visitor_id))
            else:
                cursor.execute("""
                    INSERT INTO visitor_identities (visitor_id, first_seen, last_seen, user_id, has_account, device_type, browser, ip_address, visit_count, city, region, country, org_isp, os_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """, (visitor_id, now_utc, now_utc, valid_user_id, has_acc, device_type, browser, ip, geo.get("city", ""), geo.get("region", ""), geo.get("country", "IN"), geo.get("isp", ""), os_name))

            # Also log page_view in visitor_activity_log
            cursor.execute("""
                INSERT INTO visitor_activity_log (
                    visitor_id, user_id, username, action_type, action_detail,
                    path, ip_address, city, region, country, isp,
                    device_type, os_name, browser, created_at
                ) VALUES (?, ?, ?, 'page_view', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                visitor_id, valid_user_id, (row["user_id"] if row and row["user_id"] else "Guest"),
                (referrer[:100] if referrer else 'Direct visit'), path[:100], ip,
                geo.get("city", ""), geo.get("region", ""), geo.get("country", ""), geo.get("isp", ""),
                device_type, os_name, browser, now_utc
            ))

            # Record pageview
            cursor.execute("""
                INSERT INTO site_pageviews (visitor_id, timestamp, path, referrer)
                VALUES (?, ?, ?, ?)
            """, (visitor_id, now_utc, path, referrer[:255] if referrer else ""))

            conn.commit()
            return {"status": "ok", "visitor_id": visitor_id, "device_type": device_type}
        except Exception as e:
            logger.error("Error in record_visitor_hit: %s", e)
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()


def record_visitor_heartbeat(visitor_id: str, user_id: Optional[str] = None) -> int:
    """
    Pulses active heartbeat for the visitor. Returns the active online count across the last 5 minutes.
    """
    if not visitor_id:
        return 0
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Verify if user_id exists if provided
            valid_user_id = None
            if user_id:
                cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                if cursor.fetchone():
                    valid_user_id = user_id

            if valid_user_id:
                cursor.execute("""
                    UPDATE visitor_identities 
                    SET last_seen = ?, user_id = ?, has_account = 1 
                    WHERE visitor_id = ?
                """, (now_utc, valid_user_id, visitor_id))
            else:
                cursor.execute("""
                    UPDATE visitor_identities 
                    SET last_seen = ? 
                    WHERE visitor_id = ?
                """, (now_utc, visitor_id))

            # Count distinct active visitors in last 5 minutes
            five_min_ago = (datetime.utcnow() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT count(*) as active_cnt FROM visitor_identities WHERE last_seen >= ?", (five_min_ago,))
            row = cursor.fetchone()
            active_cnt = row["active_cnt"] if row else 1

            conn.commit()
            return max(1, int(active_cnt))
        except Exception as e:
            logger.error("Error in record_visitor_heartbeat: %s", e)
            return 1
        finally:
            conn.close()


def link_visitor_to_account(visitor_id: str, user_id: str) -> bool:
    """
    Links an anonymous visitor ID to an authenticated user ID upon registration or login.
    Seamlessly transfers past guest activity logs and display active seconds into the registered user account!
    """
    if not visitor_id or not user_id:
        return False
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                return False
            uname = user["username"]

            # 1. Update visitor_identities
            cursor.execute("""
                UPDATE visitor_identities 
                SET user_id = ?, has_account = 1 
                WHERE visitor_id = ?
            """, (user_id, visitor_id))

            # 2. Transfer past guest activity logs to this registered user
            cursor.execute("""
                UPDATE visitor_activity_log
                SET user_id = ?, username = ?
                WHERE visitor_id = ? AND (user_id IS NULL OR username = 'Guest')
            """, (user_id, uname, visitor_id))

            # 3. Add guest display seconds to user total active seconds
            cursor.execute("SELECT total_active_seconds FROM visitor_identities WHERE visitor_id = ?", (visitor_id,))
            v_row = cursor.fetchone()
            if v_row and v_row["total_active_seconds"]:
                guest_secs = int(v_row["total_active_seconds"])
                cursor.execute("""
                    UPDATE users 
                    SET total_active_seconds = COALESCE(total_active_seconds, 0) + ? 
                    WHERE id = ?
                """, (guest_secs, user_id))

            conn.commit()
            logger.info("Transferred guest activity from %s to registered user %s (%s)", visitor_id, uname, user_id)
            return True
        except Exception as e:
            logger.error("Error in link_visitor_to_account: %s", e)
            return False
        finally:
            conn.close()


def get_visitor_analytics_summary() -> Dict[str, Any]:
    """
    Aggregates full executive visitor metrics:
    - Active users right now (last 5 minutes)
    - Total unique visitors
    - Total registered users vs. guest visitors
    - Signup conversion rate %
    - Mobile vs. Desktop breakdown
    - Total pageviews
    """
    five_min_ago = (datetime.utcnow() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # 1. Active Users (last 5 min)
            cursor.execute("SELECT count(*) as active_all FROM visitor_identities WHERE last_seen >= ?", (five_min_ago,))
            active_all = int(cursor.fetchone()["active_all"] or 0)

            cursor.execute("SELECT count(*) as active_reg FROM visitor_identities WHERE last_seen >= ? AND has_account = 1", (five_min_ago,))
            active_reg = int(cursor.fetchone()["active_reg"] or 0)
            active_guest = max(0, active_all - active_reg)

            # 2. Total Unique Visitors
            cursor.execute("SELECT count(*) as total_unique FROM visitor_identities")
            total_unique = int(cursor.fetchone()["total_unique"] or 0)

            # 3. Unique Visitors with Account vs Without Account
            cursor.execute("SELECT count(*) as reg_visitors FROM visitor_identities WHERE has_account = 1")
            reg_visitors = int(cursor.fetchone()["reg_visitors"] or 0)
            guest_visitors = max(0, total_unique - reg_visitors)

            # 4. Total Pageviews
            cursor.execute("SELECT count(*) as total_views FROM site_pageviews")
            total_views = int(cursor.fetchone()["total_views"] or 0)

            # 5. Total Registered Accounts in Database (Excluding system admin)
            cursor.execute("SELECT count(*) as total_accounts FROM users WHERE role != 'admin'")
            total_accounts = int(cursor.fetchone()["total_accounts"] or 0)

            # 6. Device Breakdown
            cursor.execute("SELECT device_type, count(*) as cnt FROM visitor_identities GROUP BY device_type")
            dev_rows = cursor.fetchall()
            devices = {r["device_type"]: int(r["cnt"]) for r in dev_rows}
            total_dev = sum(devices.values()) or 1
            mobile_pct = round((devices.get("Mobile", 0) / total_dev) * 100, 1)
            desktop_pct = round((devices.get("Desktop", 0) / total_dev) * 100, 1)

            conv_rate = round((reg_visitors / total_unique) * 100, 2) if total_unique > 0 else 0.0

            return {
                "status": "ok",
                "active_online": max(1, active_all),
                "active_registered": active_reg,
                "active_guests": active_guest,
                "total_unique_visitors": total_unique,
                "registered_visitors": reg_visitors,
                "guest_visitors": guest_visitors,
                "total_registered_accounts": total_accounts,
                "conversion_rate_pct": conv_rate,
                "total_pageviews": total_views,
                "device_breakdown": {
                    "mobile_pct": mobile_pct,
                    "desktop_pct": desktop_pct,
                    "raw": devices
                },
                "timestamp": datetime.now().strftime("%I:%M:%S %p")
            }
        except Exception as e:
            logger.error("Error in get_visitor_analytics_summary: %s", e)
            return {
                "status": "error",
                "active_online": 1,
                "active_registered": 0,
                "active_guests": 1,
                "total_unique_visitors": 0,
                "registered_visitors": 0,
                "guest_visitors": 0,
                "total_registered_accounts": 0,
                "conversion_rate_pct": 0.0,
                "total_pageviews": 0,
                "device_breakdown": {"mobile_pct": 50.0, "desktop_pct": 50.0, "raw": {}},
                "timestamp": datetime.now().strftime("%I:%M:%S %p")
            }
        finally:
            conn.close()
# -------------------------------------------------------------
# 📩 USER FEEDBACK & DEVELOPER REQUESTS ENGINE
# -------------------------------------------------------------

def save_user_feedback(user_id: str = "guest", username: str = "Guest Trader", email: str = "", ip_address: str = "", message: str = "") -> int:
    """Stores a user or guest feedback/support request into SQLite database."""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_feedback (user_id, username, email, ip_address, message, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'unread', CURRENT_TIMESTAMP)
            """, (user_id, username, email, ip_address, message.strip()))
            conn.commit()
            last_id = cursor.lastrowid
            logger.info("Saved user feedback #%d from %s (%s)", last_id, username, ip_address)
            return last_id
        finally:
            conn.close()


def get_all_feedback_admin(limit: int = 200, status_filter: str = "all") -> List[Dict[str, Any]]:
    """Retrieves feedback/custom requests for the admin command center."""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if status_filter in ("unread", "read", "resolved"):
                cursor.execute("""
                    SELECT id, user_id, username, email, ip_address, message, status, created_at
                    FROM user_feedback
                    WHERE status = ?
                    ORDER BY id DESC LIMIT ?
                """, (status_filter, limit))
            else:
                cursor.execute("""
                    SELECT id, user_id, username, email, ip_address, message, status, created_at
                    FROM user_feedback
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cursor.fetchall()
            res = []
            for r in rows:
                res.append({
                    "id": r["id"],
                    "user_id": r["user_id"] or "guest",
                    "username": r["username"] or "Guest Trader",
                    "email": r["email"] or "",
                    "ip_address": r["ip_address"] or "",
                    "message": r["message"] or "",
                    "status": r["status"] or "unread",
                    "created_at": str(r["created_at"])
                })
            return res
        finally:
            conn.close()


def update_feedback_status_admin(feedback_id: int, new_status: str) -> bool:
    """Updates status of a feedback entry ('unread', 'read', 'resolved')."""
    with _db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE user_feedback SET status = ? WHERE id = ?", (new_status, feedback_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
