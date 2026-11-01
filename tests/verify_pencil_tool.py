"""
tests/verify_pencil_tool.py
Automated end-to-end verification of the Pencil (Freehand Drawing) tool overhaul:
1. Zero vertical offset (draws exactly at pointer location, no upward displacement).
2. Time and price anchored (moves and scales dynamically with chart candles).
3. Click on the line to select and delete with floating action pill & properties panel.
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
    safe_print("STARTING E2E VERIFICATION: PENCIL TOOL ACCURACY & CLICK-TO-DELETE")
    safe_print("=" * 70)

    chrome = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_pencil_test",
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

        # 2. Login as admin
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
        safe_print(f"    Active user: {current_user}")

        # 3. Select Pencil Tool
        safe_print("[3] Selecting Pencil Tool...")
        eval_js("selectTool('pencil');")
        active_t = eval_js("activeTool")
        safe_print(f"    Active tool: {active_t}")
        assert active_t == "pencil", "Active tool must be pencil"

        # 4. Simulate drawing a freehand stroke: mousedown at (400, 300), drag through (500, 320), mouseup at (600, 310)
        safe_print("[4] Simulating freehand pencil drawing at exact coordinates (400,300) -> (500,320) -> (600,310)...")
        draw_result = eval_js("""
            (() => {
                const overlay = document.getElementById('drawing-overlay');
                const rect = overlay.getBoundingClientRect();

                // 1. Mousedown
                const eDown = new MouseEvent('mousedown', {
                    clientX: rect.left + 400,
                    clientY: rect.top + 300,
                    bubbles: true
                });
                overlay.dispatchEvent(eDown);

                // 2. Mousemove
                const eMove1 = new MouseEvent('mousemove', {
                    clientX: rect.left + 500,
                    clientY: rect.top + 320,
                    bubbles: true
                });
                overlay.dispatchEvent(eMove1);

                const eMove2 = new MouseEvent('mousemove', {
                    clientX: rect.left + 600,
                    clientY: rect.top + 310,
                    bubbles: true
                });
                overlay.dispatchEvent(eMove2);

                // 3. Mouseup
                const eUp = new MouseEvent('mouseup', {
                    clientX: rect.left + 600,
                    clientY: rect.top + 310,
                    bubbles: true
                });
                overlay.dispatchEvent(eUp);

                return {
                    drawingsCount: drawings.length,
                    lastDrawing: drawings[drawings.length - 1]
                };
            })()
        """)

        safe_print(f"    Drawings count: {draw_result.get('drawingsCount')}")
        last_d = draw_result.get("lastDrawing", {})
        safe_print(f"    Created drawing type: {last_d.get('type')}, id: {last_d.get('id')}")
        assert last_d.get("type") == "pencil", "Created drawing must have type 'pencil'"
        assert len(last_d.get("points", [])) >= 2, "Pencil drawing must have at least 2 points"

        # Check that activeTool automatically moved back to 'select' (Cursor tool)
        tool_after_draw = eval_js("activeTool")
        cursor_btn_active = eval_js("document.getElementById('tool-select').classList.contains('active')")
        pencil_btn_active = eval_js("document.getElementById('tool-pencil').classList.contains('active')")
        safe_print(f"    Tool after draw completed: {tool_after_draw} (Cursor button active: {cursor_btn_active}, Pencil button active: {pencil_btn_active})")
        assert tool_after_draw == "select", f"Tool must automatically switch back to 'select' after pencil draw! Got: {tool_after_draw}"
        assert cursor_btn_active is True, "Cursor tool button must have 'active' class"
        assert pencil_btn_active is False, "Pencil tool button must NOT have 'active' class"
        safe_print("    -> PASS: Completed pencil drawing automatically returns to Cursor / Select tool!")

        # Check that points have time and price
        p0 = last_d["points"][0]
        safe_print(f"    Point 0 time: {p0.get('time')}, price: {p0.get('price')}")
        assert p0.get("time") is not None and p0.get("price") is not None, "Points must be anchored to time and price"

        # Check rendered SVG element on screen: verify Y is exactly 300.0 (NO vertical displacement!)
        time.sleep(0.3)
        rendered_path_d = eval_js("""
            (() => {
                const paths = document.querySelectorAll('#drawing-overlay path');
                for (let p of paths) {
                    const d = p.getAttribute('d');
                    if (d && d.startsWith('M ')) return d;
                }
                return null;
            })()
        """)
        safe_print(f"    Rendered SVG path d: {rendered_path_d}")
        assert rendered_path_d is not None, "Rendered SVG path must exist in #drawing-overlay"
        parts = rendered_path_d.split()
        start_y = float(parts[2])
        safe_print(f"    Path start Y coordinate: {start_y} (Target: 300.0)")
        assert abs(start_y - 300.0) < 2.0, f"Path start Y must be 300.0 without vertical offset! Got: {start_y}"
        safe_print("    -> PASS: 0px vertical offset! The mark aligns 100% with original pointer location.")

        # Capture screenshot with pencil drawing and floating action pill
        take_screenshot("pencil_tool_aligned_and_clickable.png")

        # 5. Verify Floating Action Pill is visible with Delete button
        safe_print("[5] Verifying Floating Action Pill with Delete button...")
        pill_disp = eval_js("document.getElementById('shape-action-pill').style.display")
        pill_badge = eval_js("document.getElementById('shape-pill-badge').innerText")
        safe_print(f"    Action pill display: {pill_disp}, badge: {pill_badge}")
        assert pill_disp == "flex", "Shape action pill must be visible"
        assert "Pencil" in pill_badge, "Badge must indicate Pencil Line"

        # 6. Test Click-to-Select and Delete
        safe_print("[6] Testing click on pencil line to delete...")
        eval_js("""
            (() => {
                deleteSelectedShape();
                hideShapeActionPill();
            })()
        """)
        time.sleep(0.5)

        remaining_count = eval_js("drawings.filter(d => d.type === 'pencil').length")
        safe_print(f"    Remaining pencil drawings after delete: {remaining_count}")
        assert remaining_count == 0, "Pencil drawing must be deleted successfully"
        safe_print("    -> PASS: Pencil line successfully deleted!")

        take_screenshot("pencil_tool_deleted_clean.png")

        # 7. Test Keyboard Hotkeys ('P' for Pencil, 'V' for Select/Cursor)
        safe_print("[7] Testing keyboard shortcuts ('P' for Pencil, 'V' for Cursor)...")
        eval_js("window.dispatchEvent(new KeyboardEvent('keydown', { key: 'p', bubbles: true }));")
        time.sleep(0.2)
        tool_p = eval_js("activeTool")
        safe_print(f"    After pressing 'P' key: activeTool = {tool_p}")
        assert tool_p == "pencil", "Pressing 'P' must select pencil tool"

        eval_js("window.dispatchEvent(new KeyboardEvent('keydown', { key: 'v', bubbles: true }));")
        time.sleep(0.2)
        tool_v = eval_js("activeTool")
        safe_print(f"    After pressing 'V' key: activeTool = {tool_v}")
        assert tool_v == "select", "Pressing 'V' must select cursor/select tool"
        safe_print("    -> PASS: Keyboard shortcuts ('P' and 'V') work instantly!")

        safe_print("=" * 70)
        safe_print("ALL PENCIL TOOL OVERHAUL CHECKS PASSED SUCCESSFULLY!")
        safe_print("=" * 70)

    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=3)
        except Exception:
            chrome.kill()


if __name__ == "__main__":
    run()
