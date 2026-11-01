# -*- coding: utf-8 -*-
"""
Cloudflare Tunnel Launcher with Automatic Telegram Broadcast.
Captures the live trycloudflare.com URL and instantly sends it to your Telegram channel/chat.
"""
import os
import re
import sys
import shutil
import subprocess
from datetime import datetime
import pytz

# Setup IST timezone
IST = pytz.timezone("Asia/Kolkata")

def find_cloudflared_binary():
    """Locate cloudflared executable."""
    cmd = shutil.which("cloudflared")
    if cmd:
        return cmd
    common_paths = [
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return "cloudflared"

def broadcast_to_telegram(tunnel_url: str):
    """Sends the new live link to Telegram using the existing notifier."""
    try:
        from engine.telegram_notifier import TelegramNotifier
        notifier = TelegramNotifier()
        if not notifier.is_configured:
            print("[Telegram] Bot token or Chat ID not configured in .env. Skipping broadcast.")
            return

        now_str = datetime.now(IST).strftime("%d %b %Y, %I:%M %p")
        message = (
            f"🚀 <b>NIFTY 50 Trading Platform is LIVE!</b>\n\n"
            f"📈 <b>Today's Live Web Terminal:</b>\n"
            f"👉 <a href='{tunnel_url}'>{tunnel_url}</a>\n\n"
            f"⚡ <i>Clean HTTPS • Zero Warnings • Real-time Buy/Sell Signals & Drawing Tools</i>\n"
            f"⏰ <b>Session Started:</b> {now_str}"
        )
        ok, res = notifier.send_message(message, parse_mode="HTML")
        if ok:
            print(f"[Telegram] Successfully sent live link to Telegram!")
        else:
            print(f"[Telegram] Failed to send: {res}")
    except Exception as e:
        print(f"[Telegram] Error sending message: {e}")

def main():
    cf_bin = find_cloudflared_binary()
    print("=" * 65)
    print("  CLOUDFLARE SECURE TUNNEL + TELEGRAM AUTO-BROADCAST")
    print(f"  Binary: {cf_bin}")
    print("  Target: http://127.0.0.1:8000")
    print("=" * 65)

    cmd = [cf_bin, "tunnel", "--url", "http://127.0.0.1:8000"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    url_found = False
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    try:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

            if not url_found:
                match = url_pattern.search(line)
                if match:
                    url_found = True
                    tunnel_url = match.group(0)
                    print("\n" + "=" * 65)
                    print(f"  SUCCESS! NEW PUBLIC LINK: {tunnel_url}")
                    print("=" * 65 + "\n")

                    # Save to local text file
                    with open("latest_session_url.txt", "w", encoding="utf-8") as f:
                        f.write(tunnel_url)

                    # Automatically broadcast to Telegram
                    broadcast_to_telegram(tunnel_url)
    except KeyboardInterrupt:
        print("\nStopping Cloudflare Tunnel...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
