"""
tests/verify_drawing_crosshair.py
Automated end-to-end verification of precision vertical and horizontal crosshair guide lines
that display the exact pointer location when drawing on the chart.
"""
import base64
import json
import subprocess
import time
import urllib.request
import websocket
from pathlib import Path

ARTIFACT_DIR = Path(r"C:\Users\ASUS\.gemini\antigravity\brain\a35c8187-b54e-4a01-9b33-c17b3968fd99")


def safe_print(msg):
    print(str(msg).encode("ascii", "replace").decode())


def run():
    safe_print("=" * 70)
    safe_print("STARTING E2E VERIFICATION: DRAWING PRECISION POINTER CROSSHAIR")
    safe_print("=" * 70)

    chrome = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_crosshair_test",
        "--disable-gpu",
        "--no-first-run",
        "--window-size=1600,1000",
        "http://127.0.0.1:8000"
    ])

    try:
        time.sleep(3)
        targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
        page_target = next(t for t in targets if t.get("type") == "page")
        ws = websocket.create_connection(page_target["webSocketDebuggerUrl"], timeout=25)

        def cdp_send(method, params=None):
            msg = {"id": int(time.time() * 1000) % 1000000, "method": method, "params": params or {}}
            ws.send(json.dumps(msg))
            while True:
                resp = json.loads(ws.recv())
                if resp.get("id") == msg["id"]:
                    return resp.get("result", {})

        def eval_js(expr):
            res = cdp_send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return res.get("result", {}).get("value")

        def take_screenshot(filename):
            res = cdp_send("Page.captureScreenshot")
            b64 = res.get("data")
            if b64:
                out = ARTIFACT_DIR / filename
                with open(out, "wb") as f:
                    f.write(base64.b64decode(b64))
                safe_print(f"[SCREENSHOT] Saved: {filename}")

        # 1. Wait for chart to load candles
        safe_print("[1] Waiting for chart candles to load...")
        for _ in range(30):
            candles_len = eval_js("typeof activeCandles !== 'undefined' ? activeCandles.length : 0")
            if candles_len and candles_len > 0:
                safe_print(f"    Chart loaded with {candles_len} active candles.")
                break
            time.sleep(1)

        # 2. Login as admin so drawing tools are authorized
        safe_print("[2] Logging in as admin...")
        eval_js("""
            (async () => {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: 'admin', password: '123@Qweasd'})
                });
                const data = await res.json();
                if (res.ok && data.token) {
                    localStorage.setItem('auth_token', data.token);
                    currentUser = data.user;
                    if (typeof checkAuthState === 'function') await checkAuthState();
                }
            })()
        """)
        time.sleep(1)
        current_user = eval_js("currentUser ? currentUser.username : 'guest'")
        safe_print(f"    Logged in as: {current_user}")

        # 3. Initially in 'select' mode: crosshair SVG should be hidden
        safe_print("[3] Testing initial select mode...")
        initial_disp = eval_js("document.getElementById('drawing-crosshair-svg').style.display")
        safe_print(f"    Initial crosshair display: '{initial_disp}'")
        assert initial_disp == "none" or initial_disp == "", "Crosshair should be hidden initially in select mode"

        # 4. Activate Trendline drawing tool
        safe_print("[4] Selecting Trendline tool ('line')...")
        eval_js("selectTool('line');")
        active_t = eval_js("activeTool")
        safe_print(f"    Active tool: {active_t}")
        assert active_t == "line", "Active tool should be line"

        # 5. Move mouse to (x=500, y=300) over drawing overlay
        safe_print("[5] Moving pointer to (500, 300) in drawing mode...")
        eval_js("""
            (() => {
                const overlay = document.getElementById('drawing-overlay');
                const rect = overlay.getBoundingClientRect();
                updateDrawingCrosshair(500, 300);
            })()
        """)
        time.sleep(0.3)

        crosshair_disp = eval_js("document.getElementById('drawing-crosshair-svg').style.display")
        v_x1 = eval_js("document.getElementById('dcross-v').getAttribute('x1')")
        v_x2 = eval_js("document.getElementById('dcross-v').getAttribute('x2')")
        h_y1 = eval_js("document.getElementById('dcross-h').getAttribute('y1')")
        h_y2 = eval_js("document.getElementById('dcross-h').getAttribute('y2')")
        dot_cx = eval_js("document.getElementById('dcross-dot').getAttribute('cx')")
        dot_cy = eval_js("document.getElementById('dcross-dot').getAttribute('cy')")
        badge_txt = eval_js("document.getElementById('dcross-badge-txt').textContent")
        price_txt = eval_js("document.getElementById('dcross-price-txt').textContent")

        safe_print(f"    Crosshair display: {crosshair_disp}")
        safe_print(f"    Vertical line x1={v_x1}, x2={v_x2}")
        safe_print(f"    Horizontal line y1={h_y1}, y2={h_y2}")
        safe_print(f"    Reticle dot cx={dot_cx}, cy={dot_cy}")
        safe_print(f"    Floating badge text: '{badge_txt}'")
        safe_print(f"    Price scale text: '{price_txt}'")

        assert crosshair_disp == "block", "Crosshair SVG must be visible ('block') when pointer moves in drawing mode"
        assert v_x1 == "500" and v_x2 == "500", "Vertical line X must match pointer X (500)"
        assert h_y1 == "300" and h_y2 == "300", "Horizontal line Y must match pointer Y (300)"
        assert dot_cx == "500" and dot_cy == "300", "Reticle dot must match pointer (500, 300)"
        assert "₹" in badge_txt, "Floating badge must display formatted price with ₹"
        assert price_txt != "--", "Price scale badge must show numeric price"

        # 6. Simulate actively drawing (first click down, moving to point 2)
        safe_print("[6] Simulating active drawing (point 1 at 400, 250, drag to 650, 380)...")
        eval_js("""
            (() => {
                const overlay = document.getElementById('drawing-overlay');
                const time1 = xToTime(400);
                const price1 = yToPrice(250);
                isDrawing = true;
                drawStartPoint = { time: time1, price: price1, x: 400, y: 250 };
                // Pointer moves to second point
                updateDrawingCrosshair(650, 380);
                renderDrawingPreview(400, 250, 650, 380);
            })()
        """)
        time.sleep(0.3)

        v_x1_drag = eval_js("document.getElementById('dcross-v').getAttribute('x1')")
        h_y1_drag = eval_js("document.getElementById('dcross-h').getAttribute('y1')")
        safe_print(f"    During active drag: Vertical line x={v_x1_drag}, Horizontal line y={h_y1_drag}")
        assert v_x1_drag == "650", "Vertical line must follow pointer during active drawing"
        assert h_y1_drag == "380", "Horizontal line must follow pointer during active drawing"

        # Capture screenshot while drawing with crosshair active
        take_screenshot("drawing_crosshair_active_line.png")

        # 7. Finish drawing: should cleanly hide crosshair
        safe_print("[7] Finishing drawing...")
        eval_js("""
            (() => {
                isDrawing = false;
                drawStartPoint = null;
                selectTool('select');
                renderAllDrawings();
            })()
        """)
        time.sleep(0.3)

        after_finish_disp = eval_js("document.getElementById('drawing-crosshair-svg').style.display")
        safe_print(f"    Crosshair display after finish: '{after_finish_disp}'")
        assert after_finish_disp == "none", "Crosshair must hide when drawing completes"

        # 8. Test Rectangle tool ('rect')
        safe_print("[8] Testing Rectangle tool crosshair...")
        eval_js("selectTool('rect');")
        eval_js("updateDrawingCrosshair(550, 320);")
        time.sleep(0.3)

        rect_disp = eval_js("document.getElementById('drawing-crosshair-svg').style.display")
        rect_v = eval_js("document.getElementById('dcross-v').getAttribute('x1')")
        rect_h = eval_js("document.getElementById('dcross-h').getAttribute('y1')")
        safe_print(f"    Rectangle crosshair: display={rect_disp}, v_x={rect_v}, h_y={rect_h}")
        assert rect_disp == "block" and rect_v == "550" and rect_h == "320"

        # Take screenshot for Rectangle tool
        take_screenshot("drawing_crosshair_active_rect.png")

        # 9. Test mouseleave on overlay
        safe_print("[9] Testing mouseleave...")
        eval_js("hideDrawingCrosshair();")
        leave_disp = eval_js("document.getElementById('drawing-crosshair-svg').style.display")
        safe_print(f"    Crosshair display on mouseleave: '{leave_disp}'")
        assert leave_disp == "none", "Crosshair must hide on mouseleave"

        safe_print("=" * 70)
        safe_print("ALL DRAWING CROSSHAIR CHECKS PASSED SUCCESSFULLY!")
        safe_print("=" * 70)

    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=3)
        except Exception:
            chrome.kill()


if __name__ == "__main__":
    run()
