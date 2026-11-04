"""
Admin Command Center HTML Views & Component Renderers
Provides comprehensive UI for:
1. 👤 Registered Users (Profiles, Plaintext Passwords, Total Display Time, Lifecycle Actions, Timelines)
2. 🕵️ Guest Visitors (IP Geolocation, ISP, Device/OS, Display Time, IP Blocking, Timelines)
3. 🚫 Blocked Accounts & Banned IPs
4. 🛑 Account Frozen / IP Blocked Enforcement Screens
"""

import html
import json
from typing import List, Dict, Any, Optional

DEVELOPER_EMAIL = "bodrarushit@gmail.com"


def render_account_blocked_html(reason: str = "", is_ip: bool = False, entity_id: str = "") -> str:
    """
    Renders an unclosable full-screen suspension notice when a blocked IP or frozen user accesses the platform.
    """
    block_type = "IP Address Blocked" if is_ip else "Account Suspended"
    clean_reason = html.escape(reason.strip() or "Irregular activity, bad requests, or misuse of this website")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{block_type} — NIFTY 50 Pro Terminal</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #090d16;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .card {{
            background: #111827;
            border: 1px solid rgba(239, 68, 68, 0.35);
            border-radius: 16px;
            box-shadow: 0 25px 60px rgba(239, 68, 68, 0.15), 0 0 0 1px rgba(239, 68, 68, 0.2);
            max-width: 520px;
            width: 100%;
            padding: 36px 28px;
            text-align: center;
        }}
        .icon-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 64px;
            height: 64px;
            border-radius: 18px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            font-size: 30px;
            margin-bottom: 20px;
            box-shadow: 0 0 25px rgba(239, 68, 68, 0.2);
        }}
        h1 {{ font-size: 22px; font-weight: 800; color: #f87171; margin-bottom: 10px; }}
        .reason-box {{
            background: rgba(239, 68, 68, 0.08);
            border: 1px dashed rgba(239, 68, 68, 0.3);
            border-radius: 10px;
            padding: 14px 18px;
            margin: 18px 0 22px 0;
            color: #fca5a5;
            font-size: 13.5px;
            line-height: 1.5;
            text-align: left;
        }}
        .reason-box strong {{ color: #ffffff; display: block; margin-bottom: 4px; }}
        p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 22px; }}
        .contact-box {{
            background: #0b1120;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 16px;
            text-align: left;
            margin-bottom: 20px;
        }}
        .contact-box .label {{ font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
        .contact-box .email {{ font-size: 15px; font-weight: 700; color: #38bdf8; word-break: break-all; }}
        .btn-mail {{
            display: inline-block;
            width: 100%;
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            border: 1px solid #60a5fa;
            color: #ffffff;
            font-weight: 700;
            font-size: 14px;
            padding: 12px;
            border-radius: 8px;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-mail:hover {{ filter: brightness(1.15); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-badge">🚫</div>
        <h1>{block_type}</h1>
        <div class="reason-box">
            <strong>Suspension Notice:</strong>
            {clean_reason}
        </div>
        <p>Your access to NIFTY 50 Pro Terminal has been restricted by system administration due to policy violation or security monitoring.</p>
        
        <div class="contact-box">
            <div class="label">Developer & Administrator Contact</div>
            <div class="email">{DEVELOPER_EMAIL}</div>
            <div style="font-size: 11.5px; color: #64748b; margin-top: 4px;">Send an appeal email with your username or IP to request account review and unblocking.</div>
        </div>

        <a href="mailto:{DEVELOPER_EMAIL}?subject=Appeal%20Account%20Unblock&body=Hello%20Developer,%0A%0AMy%20access%20was%20restricted.%20Please%20review%20my%20account:%0AIdentifier:%20{entity_id}%0A%0AThank%20you." class="btn-mail">
            ✉️ Contact Developer to Unblock
        </a>
    </div>
</body>
</html>"""


def render_admin_command_center_html(
    users: List[Dict[str, Any]],
    guests: List[Dict[str, Any]],
    blocked: Dict[str, Any],
    admin_key: str,
    active_tab: str = "users"
) -> str:
    """
    Renders the Master User & Guest Intelligence Command Center.
    Includes:
      - Tab 1: Registered Users (Profiles, Passwords, Total Display Time, Timeline, Freeze, Purge)
      - Tab 2: Guest Visitors (IP, Geolocation, ISP, Total Display Time, Block IP, Purge, Timeline)
      - Tab 3: Blocked Accounts & Banned IPs
    """
    import html
    encoded_key = html.escape(admin_key)

    users_count = len(users)
    guests_count = len(guests)
    frozen_users = blocked.get("frozen_users", [])
    blocked_ips = blocked.get("blocked_ips", [])
    total_blocked = len(frozen_users) + len(blocked_ips)

    # 1. Build Registered Users Table Rows
    users_rows = []
    for u in users:
        uid = html.escape(str(u.get("id", "")))
        uname = html.escape(str(u.get("username", "")))
        uemail = html.escape(str(u.get("email", "")))
        uphone = html.escape(str(u.get("phone", "") or "--"))
        ustyle = html.escape(str(u.get("trading_style", "intraday_scalper")).replace("_", " ").title())
        plain_pw = html.escape(str(u.get("plain_password", "") or "--"))
        is_frozen = bool(u.get("is_frozen"))
        freeze_reason = html.escape(str(u.get("freeze_reason", "") or ""))
        reg_ist = html.escape(str(u.get("created_at_ist", "--")))
        last_login_ist = html.escape(str(u.get("last_login_ist", "--")))
        active_display = html.escape(str(u.get("active_display_str", "0 mins")))
        total_sec = u.get("total_active_seconds") or 0
        drawings_cnt = u.get("drawings_count") or 0
        copilot_cnt = u.get("copilot_queries_count") or 0
        role = html.escape(str(u.get("role", "trader")))
        accepted_ip = html.escape(str(u.get("accepted_ip", "") or "--"))

        status_pill = f'<span class="badge badge-frozen">❄️ Frozen</span>' if is_frozen else f'<span class="badge badge-active">🟢 Active</span>'
        role_pill = f'<span class="badge badge-admin">👑 Admin</span>' if role == "admin" else f'<span class="badge badge-trader">Trader</span>'

        users_rows.append(f"""
        <tr data-user-id="{uid}" data-username="{uname}" data-email="{uemail}" data-phone="{uphone}" class="user-row {'row-frozen' if is_frozen else ''}">
            <td>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div class="avatar">{(uname[:2]).upper()}</div>
                    <div>
                        <div style="font-weight: 700; color: #f8fafc; font-size: 13.5px;">{uname} {role_pill}</div>
                        <div style="font-size: 11px; color: #64748b; font-family: monospace;">{uid}</div>
                    </div>
                </div>
            </td>
            <td>
                <div style="color: #cbd5e1; font-size: 12.5px;">{uemail}</div>
                <div style="color: #94a3b8; font-size: 11.5px; font-family: monospace;">📞 {uphone}</div>
            </td>
            <td>
                <span class="pill-style">{ustyle}</span>
            </td>
            <td>
                <div style="font-size: 12px; color: #cbd5e1;">{reg_ist}</div>
                <div style="font-size: 10.5px; color: #64748b;">IP: {accepted_ip}</div>
            </td>
            <td>
                <div style="font-size: 12px; color: #cbd5e1;">{last_login_ist}</div>
            </td>
            <td>
                <div class="display-time-badge" title="Total active on-screen display time">⏱️ {active_display}</div>
            </td>
            <td>
                <div style="display: flex; gap: 6px; font-size: 11px;">
                    <span class="pill-metric" title="Saved chart drawings">🎨 {drawings_cnt}</span>
                    <span class="pill-metric" title="AI Copilot questions asked">🤖 {copilot_cnt}</span>
                </div>
            </td>
            <td>{status_pill}</td>
            <td style="text-align: right;">
                <button class="btn btn-view" onclick="openUserProfileModal({html.escape(json.dumps(u))})">
                    👁️ View Profile & Timeline
                </button>
            </td>
        </tr>
        """)

    # 2. Build Guest Visitors Table Rows
    guests_rows = []
    for g in guests:
        vid = html.escape(str(g.get("visitor_id", "")))
        gip = html.escape(str(g.get("ip_address", "")))
        gloc = html.escape(str(g.get("location_str", "India")))
        gisp = html.escape(str(g.get("org_isp", "") or "ISP / Network"))
        gdev = html.escape(str(g.get("device_type", "Desktop")))
        gos = html.escape(str(g.get("os_name", "") or "--"))
        gbrowser = html.escape(str(g.get("browser", "") or "--"))
        gdisplay = html.escape(str(g.get("active_display_str", "0 mins")))
        gvisits = g.get("visit_count") or 1
        gactions = g.get("actions_count") or 0
        glast = html.escape(str(g.get("last_seen_ist", "--")))
        is_blocked = bool(g.get("is_blocked"))
        block_reason = html.escape(str(g.get("block_reason", "") or ""))

        status_pill = f'<span class="badge badge-frozen">🚫 Blocked IP</span>' if is_blocked else f'<span class="badge badge-active">🟢 Allowed</span>'

        guests_rows.append(f"""
        <tr data-visitor-id="{vid}" data-ip="{gip}" data-location="{gloc}" data-isp="{gisp}" class="guest-row {'row-frozen' if is_blocked else ''}">
            <td>
                <div style="font-weight: 700; color: #f8fafc; font-size: 12.5px; font-family: monospace;">{vid[:12]}...</div>
                <div style="font-size: 10.5px; color: #64748b;">Guest Visitor</div>
            </td>
            <td>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-weight: 700; color: #38bdf8; font-size: 13px; font-family: monospace;">{gip}</span>
                    <button class="btn-copy" onclick="navigator.clipboard.writeText('{gip}'); showToast('IP copied to clipboard!');" title="Copy IP">📋</button>
                </div>
                <div style="font-size: 11.5px; color: #94a3b8;">📍 {gloc}</div>
            </td>
            <td>
                <div style="font-size: 12px; color: #cbd5e1; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{gisp}">
                    🏢 {gisp}
                </div>
            </td>
            <td>
                <div style="font-size: 12px; color: #cbd5e1;">💻 {gdev} • {gos}</div>
                <div style="font-size: 10.5px; color: #64748b;">🌐 {gbrowser}</div>
            </td>
            <td>
                <div class="display-time-badge" title="Total active on-screen display time">⏱️ {gdisplay}</div>
            </td>
            <td>
                <div style="font-size: 12px; color: #cbd5e1;">{glast}</div>
                <div style="font-size: 10.5px; color: #64748b;">{gvisits} visits • {gactions} actions</div>
            </td>
            <td>{status_pill}</td>
            <td style="text-align: right;">
                <button class="btn btn-view" onclick="openGuestProfileModal({html.escape(json.dumps(g))})">
                    🔍 Inspect Guest Activity
                </button>
            </td>
        </tr>
        """)

    # 3. Build Blocked Table Rows
    blocked_rows = []
    for fu in frozen_users:
        f_uname = html.escape(str(fu.get("username", "")))
        f_uid = html.escape(str(fu.get("id", "")))
        f_reason = html.escape(str(fu.get("freeze_reason", "Policy violation")))
        f_at = html.escape(str(fu.get("frozen_at", "--")))
        blocked_rows.append(f"""
        <tr>
            <td><span class="badge badge-frozen">❄️ User Account</span></td>
            <td><strong>{f_uname}</strong> ({f_uid})</td>
            <td style="color: #f87171;">{f_reason}</td>
            <td style="font-size: 12px; color: #94a3b8;">{f_at}</td>
            <td style="text-align: right;">
                <button class="btn btn-unblock" onclick="unfreezeUser('{f_uid}', '{f_uname}')">🔓 Unfreeze Account</button>
            </td>
        </tr>
        """)

    for bi in blocked_ips:
        b_ip = html.escape(str(bi.get("ip_address", "")))
        b_reason = html.escape(str(bi.get("reason", "Malicious activity")))
        b_at = html.escape(str(bi.get("blocked_at", "--")))
        blocked_rows.append(f"""
        <tr>
            <td><span class="badge badge-frozen">🚫 IP Address</span></td>
            <td><strong style="font-family: monospace; color: #f87171;">{b_ip}</strong></td>
            <td style="color: #fca5a5;">{b_reason}</td>
            <td style="font-size: 12px; color: #94a3b8;">{b_at}</td>
            <td style="text-align: right;">
                <button class="btn btn-unblock" onclick="unblockIp('{b_ip}')">🔓 Unblock IP</button>
            </td>
        </tr>
        """)

    users_table_content = "\n".join(users_rows) if users_rows else '<tr><td colspan="9" style="text-align:center; padding: 40px; color: #64748b;">No registered users found.</td></tr>'
    guests_table_content = "\n".join(guests_rows) if guests_rows else '<tr><td colspan="8" style="text-align:center; padding: 40px; color: #64748b;">No guest visitors recorded yet.</td></tr>'
    blocked_table_content = "\n".join(blocked_rows) if blocked_rows else '<tr><td colspan="5" style="text-align:center; padding: 40px; color: #22c55e;">✓ No accounts or IPs are currently blocked.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User & Guest Command Center — NIFTY 50 Pro Terminal</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #090d16;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            padding-bottom: 20px;
            border-bottom: 1px solid #1e293b;
            margin-bottom: 24px;
        }}
        .brand {{ display: flex; align-items: center; gap: 14px; }}
        .brand-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
        }}
        h1 {{ font-size: 20px; font-weight: 800; color: #f8fafc; letter-spacing: -0.3px; }}
        .subtitle {{ font-size: 12px; color: #94a3b8; margin-top: 2px; }}
        .nav-links {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
        }}
        .btn-primary {{ background: #2563eb; color: #ffffff; border-color: #3b82f6; }}
        .btn-primary:hover {{ background: #1d4ed8; }}
        .btn-secondary {{ background: #1e293b; color: #cbd5e1; border-color: #334155; }}
        .btn-secondary:hover {{ background: #334155; color: #ffffff; }}
        .btn-csv {{ background: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.35); }}
        .btn-csv:hover {{ background: rgba(34, 197, 94, 0.25); }}
        .btn-view {{ background: rgba(56, 189, 248, 0.12); color: #38bdf8; border-color: rgba(56, 189, 248, 0.3); font-size: 11.5px; padding: 6px 10px; }}
        .btn-view:hover {{ background: rgba(56, 189, 248, 0.25); }}
        .btn-unblock {{ background: rgba(34, 197, 94, 0.15); color: #4ade80; border-color: rgba(34, 197, 94, 0.35); font-size: 11.5px; padding: 6px 12px; }}
        .btn-unblock:hover {{ background: rgba(34, 197, 94, 0.3); }}
        .btn-freeze {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.35); font-weight: 700; padding: 9px 14px; }}
        .btn-freeze:hover {{ background: rgba(239, 68, 68, 0.3); }}
        .btn-danger {{ background: #dc2626; color: #ffffff; border-color: #ef4444; font-weight: 700; padding: 9px 14px; }}
        .btn-danger:hover {{ background: #b91c1c; }}

        /* Tabs */
        .tabs-nav {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 12px;
            flex-wrap: wrap;
        }}
        .tab-btn {{
            background: #111827;
            border: 1px solid #1e293b;
            color: #94a3b8;
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 13.5px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        .tab-btn:hover {{ color: #f8fafc; border-color: #334155; }}
        .tab-btn.active {{
            background: #1e3a8a;
            border-color: #3b82f6;
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
        }}
        .tab-count {{
            background: rgba(255,255,255,0.15);
            padding: 2px 7px;
            border-radius: 10px;
            font-size: 11px;
        }}

        /* Search & Filter Bar */
        .filter-bar {{
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .search-input {{
            flex: 1;
            min-width: 250px;
            background: #0b1120;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #f8fafc;
            padding: 8px 12px;
            font-size: 13px;
            outline: none;
        }}
        .search-input:focus {{ border-color: #38bdf8; }}

        /* Table */
        .table-card {{
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .table-responsive {{ overflow-x: auto; width: 100%; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        th {{
            background: #0b1120;
            padding: 12px 14px;
            color: #94a3b8;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #1e293b;
        }}
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid rgba(30, 41, 59, 0.6);
            vertical-align: middle;
        }}
        tr:hover td {{ background: rgba(30, 41, 59, 0.4); }}
        .row-frozen td {{ background: rgba(239, 68, 68, 0.05); }}

        /* Badges & Pills */
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
        }}
        .badge-active {{ background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }}
        .badge-frozen {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); }}
        .badge-admin {{ background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }}
        .badge-trader {{ background: rgba(148, 163, 184, 0.12); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.25); }}
        .avatar {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: linear-gradient(135deg, #334155 0%, #1e293b 100%);
            border: 1px solid #475569;
            color: #38bdf8;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 12px;
        }}
        .display-time-badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            color: #38bdf8;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11.5px;
        }}
        .pill-style {{
            background: rgba(168, 85, 247, 0.12);
            border: 1px solid rgba(168, 85, 247, 0.3);
            color: #c084fc;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        .pill-metric {{
            background: #0b1120;
            border: 1px solid #1e293b;
            color: #cbd5e1;
            padding: 3px 6px;
            border-radius: 4px;
        }}
        .btn-copy {{
            background: transparent;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            font-size: 12px;
            padding: 2px 4px;
            border-radius: 4px;
        }}
        .btn-copy:hover {{ color: #ffffff; background: #334155; }}

        /* Modal / Drawer */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(4px);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .modal-card {{
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 16px;
            width: 100%;
            max-width: 780px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 25px 60px rgba(0,0,0,0.8);
        }}
        .modal-header {{
            background: #0b1120;
            padding: 18px 24px;
            border-bottom: 1px solid #1e293b;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-body {{
            padding: 24px;
            overflow-y: auto;
            flex: 1;
        }}
        .close-btn {{
            background: transparent;
            border: none;
            color: #94a3b8;
            font-size: 20px;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 6px;
        }}
        .close-btn:hover {{ color: #ffffff; background: #1e293b; }}

        /* Profile Details Box */
        .profile-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }}
        .info-cell {{
            background: #0b1120;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 12px 14px;
        }}
        .info-cell .label {{
            font-size: 11px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        .info-cell .val {{
            font-size: 13.5px;
            font-weight: 600;
            color: #f1f5f9;
            word-break: break-all;
        }}
        .password-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }}
        .btn-eye {{
            background: #1e293b;
            border: 1px solid #334155;
            color: #38bdf8;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 6px;
            cursor: pointer;
        }}
        .btn-eye:hover {{ background: #334155; }}

        /* Timeline */
        .timeline-container {{
            border-top: 1px solid #1e293b;
            padding-top: 20px;
            margin-top: 10px;
        }}
        .timeline-title {{
            font-size: 14px;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .timeline-item {{
            display: flex;
            gap: 14px;
            position: relative;
            padding-bottom: 18px;
        }}
        .timeline-item::before {{
            content: '';
            position: absolute;
            left: 17px;
            top: 28px;
            bottom: 0;
            width: 2px;
            background: #1e293b;
        }}
        .timeline-item:last-child::before {{ display: none; }}
        .timeline-icon {{
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: #0b1120;
            border: 1px solid #334155;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
            z-index: 1;
        }}
        .timeline-content {{
            flex: 1;
            background: #0b1120;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 10px 14px;
        }}
        .timeline-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }}
        .timeline-type {{ font-size: 13px; font-weight: 700; color: #f8fafc; }}
        .timeline-time {{ font-size: 11px; color: #64748b; font-family: monospace; }}
        .timeline-details {{ font-size: 12.5px; color: #94a3b8; line-height: 1.4; }}

        /* Actions Footer */
        .modal-actions {{
            background: #0b1120;
            padding: 16px 24px;
            border-top: 1px solid #1e293b;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}

        /* Toast */
        #toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            border: 1px solid #3b82f6;
            color: #ffffff;
            padding: 12px 18px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            display: none;
            z-index: 2000;
        }}
    </style>
</head>
<body>

    <div class="header">
        <div class="brand">
            <div class="brand-icon">👑</div>
            <div>
                <h1>User & Guest Intelligence Command Center</h1>
                <div class="subtitle">Complete registered profile audit, guest IP telemetry, total active display time & lifecycle management</div>
            </div>
        </div>
        <div class="nav-links">
            <a href="/api/admin/copilot/queries?admin_key={encoded_key}" class="btn btn-secondary">💬 Copilot Chat Audit</a>
            <a href="/api/admin/visitors?admin_key={encoded_key}" class="btn btn-secondary">🌐 Daily Activity Log</a>
            <a href="/api/admin/users/csv?admin_key={encoded_key}" class="btn btn-csv">📥 Download Users CSV</a>
            <a href="/" class="btn btn-primary">📈 Return to Terminal</a>
        </div>
    </div>

    <!-- Tabs Nav -->
    <div class="tabs-nav">
        <button class="tab-btn active" id="tabUsersBtn" onclick="switchTab('users')">
            👤 Registered Users <span class="tab-count">{users_count}</span>
        </button>
        <button class="tab-btn" id="tabGuestsBtn" onclick="switchTab('guests')">
            🕵️ Guest Visitors <span class="tab-count">{guests_count}</span>
        </button>
        <button class="tab-btn" id="tabBlockedBtn" onclick="switchTab('blocked')">
            🚫 Blocked & Frozen <span class="tab-count" style="background: rgba(239, 68, 68, 0.25); color: #f87171;">{total_blocked}</span>
        </button>
    </div>

    <!-- TAB 1: REGISTERED USERS -->
    <div id="sectionUsers">
        <div class="filter-bar">
            <span style="font-size: 13px; font-weight: 700; color: #94a3b8;">Filter:</span>
            <input type="text" id="userSearch" class="search-input" placeholder="Search by username, email, phone number, or ID..." onkeyup="filterUsersTable()">
            <div style="font-size: 12px; color: #64748b;">Showing <strong>{users_count}</strong> registered traders</div>
        </div>

        <div class="table-card">
            <div class="table-responsive">
                <table id="usersTable">
                    <thead>
                        <tr>
                            <th>User Profile</th>
                            <th>Contact</th>
                            <th>Trading Style</th>
                            <th>Registered (IST)</th>
                            <th>Last Login (IST)</th>
                            <th>Display Active Time</th>
                            <th>Activity Counts</th>
                            <th>Status</th>
                            <th style="text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users_table_content}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- TAB 2: GUEST VISITORS -->
    <div id="sectionGuests" style="display: none;">
        <div class="filter-bar">
            <span style="font-size: 13px; font-weight: 700; color: #94a3b8;">Filter:</span>
            <input type="text" id="guestSearch" class="search-input" placeholder="Search by IP address, city, region, or ISP network..." onkeyup="filterGuestsTable()">
            <div style="font-size: 12px; color: #64748b;">Showing <strong>{guests_count}</strong> anonymous visitors</div>
        </div>

        <div class="table-card">
            <div class="table-responsive">
                <table id="guestsTable">
                    <thead>
                        <tr>
                            <th>Visitor ID</th>
                            <th>IP & Location</th>
                            <th>ISP / Network</th>
                            <th>Device & OS</th>
                            <th>Display Active Time</th>
                            <th>Last Seen (IST)</th>
                            <th>Status</th>
                            <th style="text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {guests_table_content}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- TAB 3: BLOCKED & FROZEN -->
    <div id="sectionBlocked" style="display: none;">
        <div class="table-card">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Entity Type</th>
                            <th>Identity / Target</th>
                            <th>Suspension Reason</th>
                            <th>Blocked Timestamp</th>
                            <th style="text-align: right;">Unblock Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {blocked_table_content}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- MODAL: REGISTERED USER PROFILE & TIMELINE -->
    <div class="modal-overlay" id="userModal">
        <div class="modal-card">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div class="avatar" id="mUserAvatar">TR</div>
                    <div>
                        <h2 style="font-size: 16px; font-weight: 800; color: #f8fafc;" id="mUserName">Trader</h2>
                        <div style="font-size: 11px; color: #64748b;" id="mUserId">ID</div>
                    </div>
                </div>
                <button class="close-btn" onclick="closeUserModal()">✕</button>
            </div>
            <div class="modal-body">
                <div class="profile-grid">
                    <div class="info-cell">
                        <div class="label">Email Address</div>
                        <div class="val" id="mUserEmail">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Mobile Number</div>
                        <div class="val" id="mUserPhone">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Trading Style</div>
                        <div class="val" id="mUserStyle">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Registration Password</div>
                        <div class="password-row">
                            <span class="val" id="mUserPw" style="font-family: monospace;">••••••••</span>
                            <button class="btn-eye" id="mUserPwToggle" onclick="togglePasswordView()">👁️ Show</button>
                        </div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Total Display Active Time</div>
                        <div class="val" id="mUserDisplayTime" style="color: #38bdf8;">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Registration Date (IST)</div>
                        <div class="val" id="mUserCreated">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Last Login (IST)</div>
                        <div class="val" id="mUserLastLogin">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Registration IP</div>
                        <div class="val" id="mUserIp">--</div>
                    </div>
                </div>

                <!-- Timeline Section -->
                <div class="timeline-container">
                    <div class="timeline-title">
                        <span>📅 Chronological Activity Timeline (Registration to Live)</span>
                        <span id="mTimelineCount" style="font-size: 12px; color: #64748b;">Loading timeline...</span>
                    </div>
                    <div id="mTimelineList">
                        <div style="text-align: center; padding: 20px; color: #64748b;">Fetching timeline...</div>
                    </div>
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-danger" id="mBtnDelete" onclick="deleteUserCompletely()">
                    🗑️ Delete User Completely
                </button>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-freeze" id="mBtnFreeze" onclick="toggleFreezeUser()">
                        ❄️ Freeze User Account
                    </button>
                    <button class="btn btn-secondary" onclick="closeUserModal()">Close</button>
                </div>
            </div>
        </div>
    </div>

    <!-- MODAL: GUEST VISITOR PROFILE & TIMELINE -->
    <div class="modal-overlay" id="guestModal">
        <div class="modal-card">
            <div class="modal-header">
                <div>
                    <h2 style="font-size: 16px; font-weight: 800; color: #f8fafc;" id="mGuestTitle">Guest Visitor</h2>
                    <div style="font-size: 11px; color: #64748b;" id="mGuestId">ID</div>
                </div>
                <button class="close-btn" onclick="closeGuestModal()">✕</button>
            </div>
            <div class="modal-body">
                <div class="profile-grid">
                    <div class="info-cell">
                        <div class="label">IP Address</div>
                        <div class="val" id="mGuestIp" style="color: #38bdf8; font-family: monospace;">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Geolocation</div>
                        <div class="val" id="mGuestLocation">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">ISP / Telecom Network</div>
                        <div class="val" id="mGuestIsp">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Device / OS / Browser</div>
                        <div class="val" id="mGuestDevice">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Total Display Active Time</div>
                        <div class="val" id="mGuestDisplayTime" style="color: #38bdf8;">--</div>
                    </div>
                    <div class="info-cell">
                        <div class="label">Visits & Actions</div>
                        <div class="val" id="mGuestVisits">--</div>
                    </div>
                </div>

                <!-- Guest Timeline -->
                <div class="timeline-container">
                    <div class="timeline-title">
                        <span>📅 Visitor Activity Timeline</span>
                        <span id="mGuestTimelineCount" style="font-size: 12px; color: #64748b;">Loading...</span>
                    </div>
                    <div id="mGuestTimelineList">
                        <div style="text-align: center; padding: 20px; color: #64748b;">Fetching guest actions...</div>
                    </div>
                </div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-danger" id="mBtnDeleteGuest" onclick="deleteGuestCompletely()">
                    🗑️ Delete Guest Data
                </button>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-freeze" id="mBtnBlockIp" onclick="toggleBlockGuestIp()">
                        🚫 Block Guest IP
                    </button>
                    <button class="btn btn-secondary" onclick="closeGuestModal()">Close</button>
                </div>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <script>
        const ADMIN_KEY = '{encoded_key}';
        let currentModalUser = null;
        let currentModalGuest = null;
        let isPwRevealed = false;

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => {{ t.style.display = 'none'; }}, 3000);
        }}

        function switchTab(tab) {{
            document.getElementById('sectionUsers').style.display = tab === 'users' ? 'block' : 'none';
            document.getElementById('sectionGuests').style.display = tab === 'guests' ? 'block' : 'none';
            document.getElementById('sectionBlocked').style.display = tab === 'blocked' ? 'block' : 'none';

            document.getElementById('tabUsersBtn').classList.toggle('active', tab === 'users');
            document.getElementById('tabGuestsBtn').classList.toggle('active', tab === 'guests');
            document.getElementById('tabBlockedBtn').classList.toggle('active', tab === 'blocked');
        }}

        function filterUsersTable() {{
            const q = (document.getElementById('userSearch').value || '').toLowerCase();
            const rows = document.querySelectorAll('#usersTable tbody tr.user-row');
            rows.forEach(r => {{
                const u = (r.getAttribute('data-username') || '').toLowerCase();
                const e = (r.getAttribute('data-email') || '').toLowerCase();
                const p = (r.getAttribute('data-phone') || '').toLowerCase();
                const id = (r.getAttribute('data-user-id') || '').toLowerCase();
                r.style.display = (u.includes(q) || e.includes(q) || p.includes(q) || id.includes(q)) ? '' : 'none';
            }});
        }}

        function filterGuestsTable() {{
            const q = (document.getElementById('guestSearch').value || '').toLowerCase();
            const rows = document.querySelectorAll('#guestsTable tbody tr.guest-row');
            rows.forEach(r => {{
                const ip = (r.getAttribute('data-ip') || '').toLowerCase();
                const loc = (r.getAttribute('data-location') || '').toLowerCase();
                const isp = (r.getAttribute('data-isp') || '').toLowerCase();
                r.style.display = (ip.includes(q) || loc.includes(q) || isp.includes(q)) ? '' : 'none';
            }});
        }}

        // Open Registered User Profile Modal
        async function openUserProfileModal(u) {{
            currentModalUser = u;
            isPwRevealed = false;

            document.getElementById('mUserAvatar').innerText = (u.username || 'TR').substring(0, 2).toUpperCase();
            document.getElementById('mUserName').innerText = u.username;
            document.getElementById('mUserId').innerText = u.id;
            document.getElementById('mUserEmail').innerText = u.email;
            document.getElementById('mUserPhone').innerText = u.phone || '--';
            document.getElementById('mUserStyle').innerText = (u.trading_style || '').replace('_', ' ').toUpperCase();
            document.getElementById('mUserPw').innerText = '••••••••';
            document.getElementById('mUserPwToggle').innerText = '👁️ Show';
            document.getElementById('mUserDisplayTime').innerText = u.active_display_str || '0 mins';
            document.getElementById('mUserCreated').innerText = u.created_at_ist || '--';
            document.getElementById('mUserLastLogin').innerText = u.last_login_ist || '--';
            document.getElementById('mUserIp').innerText = u.accepted_ip || '--';

            const freezeBtn = document.getElementById('mBtnFreeze');
            if (u.is_frozen) {{
                freezeBtn.className = 'btn btn-unblock';
                freezeBtn.innerText = '🔓 Unfreeze User Account';
            }} else {{
                freezeBtn.className = 'btn btn-freeze';
                freezeBtn.innerText = '❄️ Freeze User Account';
            }}

            document.getElementById('userModal').style.display = 'flex';
            loadUserTimeline(u.id);
        }}

        function closeUserModal() {{
            document.getElementById('userModal').style.display = 'none';
            currentModalUser = null;
        }}

        function togglePasswordView() {{
            if (!currentModalUser) return;
            isPwRevealed = !isPwRevealed;
            const pwSpan = document.getElementById('mUserPw');
            const toggleBtn = document.getElementById('mUserPwToggle');
            if (isPwRevealed) {{
                pwSpan.innerText = currentModalUser.plain_password || '(Not Captured)';
                toggleBtn.innerText = '🙈 Hide';
            }} else {{
                pwSpan.innerText = '••••••••';
                toggleBtn.innerText = '👁️ Show';
            }}
        }}

        async function loadUserTimeline(userId) {{
            const listEl = document.getElementById('mTimelineList');
            const countEl = document.getElementById('mTimelineCount');
            listEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b;">Loading full user timeline...</div>';

            try {{
                const res = await fetch(`/api/admin/user-timeline?user_id=${{encodeURIComponent(userId)}}&admin_key=${{encodeURIComponent(ADMIN_KEY)}}`);
                const data = await res.json();
                if (data.status === 'ok') {{
                    const events = data.timeline || [];
                    countEl.innerText = `${{events.length}} recorded events`;
                    if (events.length === 0) {{
                        listEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b;">No activity events recorded yet.</div>';
                        return;
                    }}
                    listEl.innerHTML = events.map(e => `
                        <div class="timeline-item">
                            <div class="timeline-icon">${{e.icon || '⚡'}}</div>
                            <div class="timeline-content">
                                <div class="timeline-header">
                                    <span class="timeline-type">${{e.title || e.type}}</span>
                                    <span class="timeline-time">${{e.timestamp_ist || e.timestamp}}</span>
                                </div>
                                <div class="timeline-details">${{e.details || ''}}</div>
                                ${{e.ip ? `<div style="font-size: 10.5px; color: #64748b; margin-top: 4px;">IP: ${{e.ip}} ${{e.location ? `• ${{e.location}}` : ''}}</div>` : ''}}
                            </div>
                        </div>
                    `).join('');
                }} else {{
                    listEl.innerHTML = `<div style="color: #f87171; padding: 10px;">Error: ${{data.message}}</div>`;
                }}
            }} catch (err) {{
                listEl.innerHTML = `<div style="color: #f87171; padding: 10px;">Failed to load timeline: ${{err.message}}</div>`;
            }}
        }}

        async function toggleFreezeUser() {{
            if (!currentModalUser) return;
            const uid = currentModalUser.id;
            const uname = currentModalUser.username;
            const isFrozen = currentModalUser.is_frozen;

            if (isFrozen) {{
                if (!confirm(`Are you sure you want to unfreeze account for trader '${{uname}}'?`)) return;
                const res = await fetch('/api/admin/user/unfreeze', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: uid, admin_key: ADMIN_KEY }})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    showToast(`Trader '${{uname}}' unblocked successfully!`);
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    alert(data.message || 'Error unfreezing user');
                }}
            }} else {{
                const reason = prompt(`Enter suspension reason for trader '${{uname}}':`, 'Irregular activity, bad requests, or misuse of this website');
                if (reason === null) return;
                const res = await fetch('/api/admin/user/freeze', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ user_id: uid, reason: reason, admin_key: ADMIN_KEY }})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    showToast(`Trader '${{uname}}' has been frozen/suspended.`);
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    alert(data.message || 'Error freezing user');
                }}
            }}
        }}

        async function unfreezeUser(uid, uname) {{
            if (!confirm(`Unfreeze and restore access for trader '${{uname}}'?`)) return;
            const res = await fetch('/api/admin/user/unfreeze', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ user_id: uid, admin_key: ADMIN_KEY }})
            }});
            const data = await res.json();
            if (data.status === 'ok') {{
                showToast(`Trader '${{uname}}' restored!`);
                setTimeout(() => location.reload(), 1000);
            }} else {{
                alert(data.message || 'Error unfreezing user');
            }}
        }}

        async function deleteUserCompletely() {{
            if (!currentModalUser) return;
            const uid = currentModalUser.id;
            const uname = currentModalUser.username;

            const confirm1 = confirm(`⚠️ CAUTION: Are you sure you want to PERMANENTLY DELETE user '${{uname}}'?\\n\\nThis will permanently purge ALL drawings, chat history, copilot questions, and preferences as if they never existed.`);
            if (!confirm1) return;

            const confirm2 = prompt(`To confirm permanent deletion, type the exact username: '${{uname}}'`);
            if (confirm2 !== uname) {{
                alert('Deletion cancelled: Username confirmation mismatch.');
                return;
            }}

            const res = await fetch('/api/admin/user/delete', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ user_id: uid, admin_key: ADMIN_KEY }})
            }});
            const data = await res.json();
            if (data.status === 'ok') {{
                alert(`User '${{uname}}' completely wiped from the platform.`);
                location.reload();
            }} else {{
                alert(data.message || 'Error deleting user');
            }}
        }}

        // Open Guest Profile Modal
        async function openGuestProfileModal(g) {{
            currentModalGuest = g;
            document.getElementById('mGuestTitle').innerText = `Guest Visitor: ${{(g.ip_address || '').substring(0, 15)}}`;
            document.getElementById('mGuestId').innerText = g.visitor_id;
            document.getElementById('mGuestIp').innerText = g.ip_address || '--';
            document.getElementById('mGuestLocation').innerText = g.location_str || 'India';
            document.getElementById('mGuestIsp').innerText = g.org_isp || '--';
            document.getElementById('mGuestDevice').innerText = `${{g.device_type || 'Desktop'}} • ${{g.os_name || '--'}} • ${{g.browser || '--'}}`;
            document.getElementById('mGuestDisplayTime').innerText = g.active_display_str || '0 mins';
            document.getElementById('mGuestVisits').innerText = `${{g.visit_count || 1}} visits • ${{g.actions_count || 0}} actions`;

            const blockBtn = document.getElementById('mBtnBlockIp');
            if (g.is_blocked) {{
                blockBtn.className = 'btn btn-unblock';
                blockBtn.innerText = '🔓 Unblock Guest IP';
            }} else {{
                blockBtn.className = 'btn btn-freeze';
                blockBtn.innerText = '🚫 Block Guest IP';
            }}

            document.getElementById('guestModal').style.display = 'flex';
            loadGuestTimeline(g.visitor_id);
        }}

        function closeGuestModal() {{
            document.getElementById('guestModal').style.display = 'none';
            currentModalGuest = null;
        }}

        async function loadGuestTimeline(visitorId) {{
            const listEl = document.getElementById('mGuestTimelineList');
            const countEl = document.getElementById('mGuestTimelineCount');
            listEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b;">Loading guest activity timeline...</div>';

            try {{
                const res = await fetch(`/api/admin/guest-timeline?visitor_id=${{encodeURIComponent(visitorId)}}&admin_key=${{encodeURIComponent(ADMIN_KEY)}}`);
                const data = await res.json();
                if (data.status === 'ok') {{
                    const events = data.timeline || [];
                    countEl.innerText = `${{events.length}} actions`;
                    if (events.length === 0) {{
                        listEl.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b;">No actions recorded yet.</div>';
                        return;
                    }}
                    listEl.innerHTML = events.map(e => `
                        <div class="timeline-item">
                            <div class="timeline-icon">${{e.icon || '⚡'}}</div>
                            <div class="timeline-content">
                                <div class="timeline-header">
                                    <span class="timeline-type">${{e.title || e.type}}</span>
                                    <span class="timeline-time">${{e.timestamp_ist || e.timestamp}}</span>
                                </div>
                                <div class="timeline-details">${{e.details || ''}}</div>
                                ${{e.ip ? `<div style="font-size: 10.5px; color: #64748b; margin-top: 4px;">IP: ${{e.ip}} ${{e.location ? `• ${{e.location}}` : ''}}</div>` : ''}}
                            </div>
                        </div>
                    `).join('');
                }} else {{
                    listEl.innerHTML = `<div style="color: #f87171; padding: 10px;">Error: ${{data.message}}</div>`;
                }}
            }} catch (err) {{
                listEl.innerHTML = `<div style="color: #f87171; padding: 10px;">Failed to load guest timeline: ${{err.message}}</div>`;
            }}
        }}

        async function toggleBlockGuestIp() {{
            if (!currentModalGuest) return;
            const ip = currentModalGuest.ip_address;
            const isBlocked = currentModalGuest.is_blocked;

            if (isBlocked) {{
                unblockIp(ip);
            }} else {{
                const reason = prompt(`Enter blocking reason for IP '${{ip}}':`, 'Irregular activity, bad requests, or misuse of this website');
                if (reason === null) return;
                const res = await fetch('/api/admin/ip/block', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ ip_address: ip, reason: reason, admin_key: ADMIN_KEY }})
                }});
                const data = await res.json();
                if (data.status === 'ok') {{
                    showToast(`IP '${{ip}}' has been blocked!`);
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    alert(data.message || 'Error blocking IP');
                }}
            }}
        }}

        async function unblockIp(ip) {{
            if (!confirm(`Unblock IP address '${{ip}}'?`)) return;
            const res = await fetch('/api/admin/ip/unblock', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ ip_address: ip, admin_key: ADMIN_KEY }})
            }});
            const data = await res.json();
            if (data.status === 'ok') {{
                showToast(`IP '${{ip}}' unblocked successfully!`);
                setTimeout(() => location.reload(), 1000);
            }} else {{
                alert(data.message || 'Error unblocking IP');
            }}
        }}

        async function deleteGuestCompletely() {{
            if (!currentModalGuest) return;
            const vid = currentModalGuest.visitor_id;
            if (!confirm(`Delete all tracking data for guest '${{vid}}'?`)) return;
            const res = await fetch('/api/admin/guest/delete', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ visitor_id: vid, admin_key: ADMIN_KEY }})
            }});
            const data = await res.json();
            if (data.status === 'ok') {{
                alert('Guest visitor data deleted successfully.');
                location.reload();
            }} else {{
                alert(data.message || 'Error deleting guest');
            }}
        }}
    </script>
</body>
</html>"""
