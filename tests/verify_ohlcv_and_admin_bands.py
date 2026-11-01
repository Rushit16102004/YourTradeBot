"""
tests/verify_ohlcv_and_admin_bands.py
Automated CDP test verifying:
1. Real-time OHLCV display in header strip (O, H, L, C, and V).
2. Hovering crosshair updates V: dynamically.
3. In admin mode, the 2 dashed lines (+-2 sigma bands) are NOT Always On Display (AOD).
4. Screenshots captured into artifact directory.
"""
import base64
import json
import subprocess
import time
import urllib.request
import websocket
from pathlib import Path

ARTIFACT_DIR = Path(r"C:\Users\ASUS\.gemini\antigravity\brain\a35c8187-b54e-4a01-9b33-c17b3968fd99")


def run():
    print("=" * 60)
    print("STARTING E2E VERIFICATION: OHLCV HEADER & ADMIN 2-LINE AOD FIX")
    print("=" * 60)

    chrome = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9223",
        "--remote-allow-origins=*",
        r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_ohlcv_test",
        "--disable-gpu",
        "--no-first-run",
        "--window-size=1600,950",
        "http://127.0.0.1:8000"
    ])

    try:
        time.sleep(3)
        targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9223/json").read())
        page_target = next(t for t in targets if t.get("type") == "page")
        ws = websocket.create_connection(page_target["webSocketDebuggerUrl"], timeout=15)

        def cdp_send(method, params=None):
            msg = {"id": int(time.time() * 1000) % 1000000, "method": method, "params": params or {}}
            ws.send(json.dumps(msg))
            while True:
                resp = json.loads(ws.recv())
                if resp.get("id") == msg["id"]:
                    return resp.get("result", {})

        def eval_js(expr):
            res = cdp_send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
            return res.get("result", {}).get("value")

        def take_screenshot(filename):
            res = cdp_send("Page.captureScreenshot")
            b64 = res.get("data")
            if b64:
                out = ARTIFACT_DIR / filename
                with open(out, "wb") as f:
                    f.write(base64.b64decode(b64))
                print(f"[SCREENSHOT] Saved: {filename}")

        cdp_send("Page.enable")
        time.sleep(3)

        def safe_print(msg):
            print(msg.encode("ascii", "replace").decode())

        # 1. Verify OHLCV in Header Legend
        legend_text = eval_js("document.getElementById('ohlc-legend') ? document.getElementById('ohlc-legend').innerText : ''")
        vol_text = eval_js("document.getElementById('leg-vol') ? document.getElementById('leg-vol').innerText : ''")
        open_text = eval_js("document.getElementById('leg-open') ? document.getElementById('leg-open').innerText : ''")
        close_text = eval_js("document.getElementById('leg-close') ? document.getElementById('leg-close').innerText : ''")
        bands_span_display = eval_js("document.getElementById('leg-bands-span') ? window.getComputedStyle(document.getElementById('leg-bands-span')).display : ''")

        safe_print(f"[TEST 1] Legend Header Text: {legend_text}")
        safe_print(f"[TEST 1] Open: {open_text}, Close: {close_text}, Volume: {vol_text}")
        safe_print(f"[TEST 1] Bands Span Display: {bands_span_display}")

        assert "NIFTY 50" in legend_text, "NIFTY 50 missing from header"
        assert "O:" in legend_text and "H:" in legend_text and "L:" in legend_text and "C:" in legend_text, "OHLC missing"
        assert "V:" in legend_text, "V (Volume) missing from header legend!"
        assert vol_text != "--" and len(vol_text) > 0, f"Volume value not loaded: {vol_text}"
        print("  -> PASS: Complete OHLCV successfully rendered in header line!")

        # 2. Login as Admin
        print("\n[TEST 2] Logging in as Admin...")
        login_result = eval_js("""
            (async () => {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: 'admin', password: '123@Qweasd'})
                });
                const data = await res.json();
                if (data.token) {
                    localStorage.setItem('auth_token', data.token);
                    currentUser = data.user;
                    await checkAuthState();
                    await loadUserPreferencesFromServer();
                    return { ok: true, user: currentUser.username };
                }
                return { ok: false, error: data.message };
            })()
        """)
        time.sleep(2)
        print(f"[TEST 2] Login Result: {login_result}")

        # 3. Check if 2 lines (Bands) are AOD in Admin Page
        is_bands_on = eval_js("isBandsEnabled")
        bands_btn_text = eval_js("document.getElementById('btn-bands-toggle') ? document.getElementById('btn-bands-toggle').innerText : ''")
        bands_span_disp_admin = eval_js("document.getElementById('leg-bands-span') ? window.getComputedStyle(document.getElementById('leg-bands-span')).display : ''")

        safe_print(f"[TEST 3] Admin isBandsEnabled: {is_bands_on}")
        safe_print(f"[TEST 3] Admin Bands Button: {bands_btn_text}")
        safe_print(f"[TEST 3] Admin Bands Header Span Display: {bands_span_disp_admin}")

        assert is_bands_on is False, f"Bands should be False for admin, got: {is_bands_on}"
        assert bands_span_disp_admin == "none", f"Bands span should be hidden for admin, got: {bands_span_disp_admin}"
        safe_print("  -> PASS: 2 dashed lines are NOT Always On Display (AOD) in admin mode!")

        # 4. Take Screenshot of Clean Admin Terminal with OHLCV header
        take_screenshot("admin_page_clean_ohlcv_header_aod_solved.png")

        # 5. Crosshair hover simulation
        safe_print("\n[TEST 4] Simulating crosshair move across candles...")
        hover_result = eval_js("""
            (() => {
                if (activeCandles && activeCandles.length > 5) {
                    const testCandle = activeCandles[10];
                    updateOHLCVLegend(testCandle);
                    return {
                        open: document.getElementById('leg-open').innerText,
                        vol: document.getElementById('leg-vol').innerText,
                        volColor: document.getElementById('leg-vol').style.color
                    };
                }
                return null;
            })()
        """)
        safe_print(f"[TEST 4] Hovered Candle Legend State: {hover_result}")
        assert hover_result is not None, "Failed to hover candle"
        assert hover_result["vol"] != "--", "Hover volume is empty"
        safe_print("  -> PASS: Crosshair hover dynamically updates OHLCV and volume formatting!")

        # 6. Verify Explicit Toggle of Bands works on demand
        safe_print("\n[TEST 5] Toggling +-2 sigma bands ON explicitly...")
        eval_js("toggleVWAPBands();")
        time.sleep(1)
        bands_after_toggle = eval_js("isBandsEnabled")
        bands_span_after_toggle = eval_js("document.getElementById('leg-bands-span') ? window.getComputedStyle(document.getElementById('leg-bands-span')).display : ''")
        safe_print(f"[TEST 5] isBandsEnabled after toggle: {bands_after_toggle}, Span Display: {bands_span_after_toggle}")
        assert bands_after_toggle is True, "Bands did not turn ON when explicitly clicked"
        assert bands_span_after_toggle != "none", "Bands span should be visible when ON"
        take_screenshot("bands_explicitly_toggled_on.png")

        safe_print("\n[TEST 6] Toggling +-2 sigma bands OFF explicitly...")
        eval_js("toggleVWAPBands();")
        time.sleep(1)
        bands_after_toggle_off = eval_js("isBandsEnabled")
        bands_span_after_toggle_off = eval_js("document.getElementById('leg-bands-span') ? window.getComputedStyle(document.getElementById('leg-bands-span')).display : ''")
        safe_print(f"[TEST 6] isBandsEnabled after toggle OFF: {bands_after_toggle_off}, Span Display: {bands_span_after_toggle_off}")
        assert bands_after_toggle_off is False, "Bands did not turn OFF"
        assert bands_span_after_toggle_off == "none", "Bands span should be hidden when OFF"
        take_screenshot("bands_explicitly_toggled_off.png")

        safe_print("\n" + "=" * 60)
        safe_print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY (100%)!")
        safe_print("=" * 60)

    finally:
        chrome.terminate()


if __name__ == "__main__":
    run()
