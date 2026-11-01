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

chrome = subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--remote-debugging-port=9232",
    "--remote-allow-origins=*",
    r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_sr_hover_test",
    "--disable-gpu",
    "--no-first-run",
    "--window-size=1600,1000",
    "http://127.0.0.1:8000"
])

try:
    time.sleep(3)
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9232/json").read())
    page_target = next(t for t in targets if t.get("type") == "page")
    ws = websocket.create_connection(page_target["webSocketDebuggerUrl"], timeout=25)

    def eval_js(expr):
        msg = {"id": int(time.time() * 1000) % 1000000, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}}
        ws.send(json.dumps(msg))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg["id"]:
                return resp.get("result", {}).get("result", {}).get("value")

    def take_screenshot(filename):
        msg = {"id": 999999, "method": "Page.captureScreenshot", "params": {}}
        ws.send(json.dumps(msg))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == 999999:
                b64 = resp.get("result", {}).get("data")
                if b64:
                    with open(ARTIFACT_DIR / filename, "wb") as f:
                        f.write(base64.b64decode(b64))
                    safe_print(f"[SCREENSHOT] Saved: {filename}")
                break

    time.sleep(1)

    # 1. Verify Privacy Policy & Model Training Notice in Modal & Footer
    safe_print("[1] Verifying Privacy Policy clause in SEBI Modal & footer...")
    has_policy_sec6 = eval_js("document.getElementById('sebi-modal-overlay').textContent.includes('Privacy Policy & AI Model Training Data Usage')")
    has_model_train_txt = eval_js("document.getElementById('sebi-modal-overlay').textContent.includes('model training purposes')")
    safe_print(f"    Privacy Policy section 6 in modal: {has_policy_sec6}")
    safe_print(f"    Model training disclosure present: {has_model_train_txt}")
    assert has_policy_sec6 and has_model_train_txt, "Privacy policy model training clause must be present"
    safe_print("    -> PASS: Privacy policy mentions user chat history stored securely for model training.")

    # 2. Check Floating Tooltip in DOM
    safe_print("\n[2] Verifying floating S&R tooltip element...")
    tooltip_exists = eval_js("document.getElementById('sr-pointer-tooltip') !== null")
    safe_print(f"    #sr-pointer-tooltip exists: {tooltip_exists}")
    assert tooltip_exists is True, "#sr-pointer-tooltip must exist in DOM"

    # 3. Enable S&R levels and mock test levels (1 Line + 1 Rectangle Zone)
    safe_print("\n[3] Setting up S&R Line and Rectangle Zone for hover testing...")
    eval_js("""
    (() => {
        isSREnabled = true;
        currentTimeframe = '5m';
        srLevelsData['5m'] = [
            {
                type: 'line',
                avg_price: 22600.0,
                price1: 22600.0,
                role: 'Resistance',
                is_support: false,
                bounces: 5,
                time1: Math.floor(Date.now() / 1000) - 3600
            },
            {
                type: 'rect',
                price1: 22520.0,
                price2: 22500.0,
                role: 'Support',
                is_support: true,
                bounces: 7,
                time1: Math.floor(Date.now() / 1000) - 7200
            }
        ];
        currentSRPeriod = '5m';
        renderAllDrawings();
    })()
    """)
    time.sleep(0.5)

    # 4. Test S&R Line hover: hover at cursor position (500, 250)
    safe_print("\n[4] Simulating mouse hover over S&R Line at (500, 250)...")
    line_hover_result = eval_js("""
    (() => {
        const groups = document.querySelectorAll('#drawing-overlay .sr-overlay-group');
        for (let g of groups) {
            const line = g.querySelector('line');
            if (line) {
                const rect = document.getElementById('main-chart-wrapper').getBoundingClientRect();
                const clientX = rect.left + 500;
                const clientY = rect.top + 250;
                g.dispatchEvent(new MouseEvent('mouseenter', { clientX, clientY, bubbles: true }));
                g.dispatchEvent(new MouseEvent('mousemove', { clientX, clientY, bubbles: true }));
                const tip = document.getElementById('sr-pointer-tooltip');
                const txt = document.getElementById('sr-pointer-text');
                return {
                    display: tip.style.display,
                    left: tip.style.left,
                    top: tip.style.top,
                    text: txt.innerText
                };
            }
        }
        return null;
    })()
    """)
    safe_print(f"    Line tooltip result: {line_hover_result}")
    assert line_hover_result is not None, "Line hover must find S&R line group"
    assert line_hover_result["display"] == "block", "Tooltip must be visible on line hover"
    assert "Resistance" in line_hover_result["text"] and "22600" in line_hover_result["text"], "Tooltip must display Resistance and price"
    assert "500px" in line_hover_result["left"], f"Tooltip left must be placed at cursor X (~500px), got {line_hover_result['left']}"
    safe_print("    -> PASS: S&R Line info displays exactly at mouse cursor point!")

    take_screenshot("sr_line_hover_at_cursor.png")

    # 5. Test S&R Rectangle Zone hover: hover at cursor position (600, 320)
    safe_print("\n[5] Simulating mouse hover over S&R Rectangle Zone at (600, 320)...")
    rect_hover_result = eval_js("""
    (() => {
        const groups = document.querySelectorAll('#drawing-overlay .sr-overlay-group');
        for (let g of groups) {
            const rect = g.querySelector('rect[stroke]');
            if (rect) {
                const wrapRect = document.getElementById('main-chart-wrapper').getBoundingClientRect();
                const clientX = wrapRect.left + 600;
                const clientY = wrapRect.top + 320;
                g.dispatchEvent(new MouseEvent('mouseenter', { clientX, clientY, bubbles: true }));
                g.dispatchEvent(new MouseEvent('mousemove', { clientX, clientY, bubbles: true }));
                const tip = document.getElementById('sr-pointer-tooltip');
                const txt = document.getElementById('sr-pointer-text');
                return {
                    display: tip.style.display,
                    left: tip.style.left,
                    top: tip.style.top,
                    text: txt.innerText
                };
            }
        }
        return null;
    })()
    """)
    safe_print(f"    Rectangle Zone tooltip result: {rect_hover_result}")
    assert rect_hover_result is not None, "Zone hover must find S&R rectangle group"
    assert rect_hover_result["display"] == "block", "Tooltip must be visible on rectangle zone hover"
    assert "Zone" in rect_hover_result["text"] and "22500" in rect_hover_result["text"], "Tooltip must display Zone info and price range"
    assert "600px" in rect_hover_result["left"], f"Tooltip left must be placed at cursor X (~600px), got {rect_hover_result['left']}"
    safe_print("    -> PASS: S&R Rectangle Zone info displays exactly at mouse cursor point!")

    take_screenshot("sr_rect_zone_hover_at_cursor.png")

    # 6. Test mouseleave
    safe_print("\n[6] Testing mouseleave hides tooltip...")
    eval_js("""
    (() => {
        const groups = document.querySelectorAll('#drawing-overlay .sr-overlay-group');
        if (groups.length > 0) {
            groups[0].dispatchEvent(new MouseEvent('mouseleave', { bubbles: true }));
        }
    })()
    """)
    disp_after = eval_js("document.getElementById('sr-pointer-tooltip').style.display")
    safe_print(f"    Tooltip display after mouseleave: {disp_after}")
    assert disp_after == "none", "Tooltip must hide on mouseleave"
    safe_print("    -> PASS: Tooltip hides cleanly when cursor leaves S&R shape.")

    safe_print("\n===================================================================")
    safe_print("ALL S&R CURSOR-TRACKING HOVER & PRIVACY POLICY CHECKS PASSED!")
    safe_print("===================================================================")

finally:
    try: ws.close()
    except Exception: pass
    chrome.kill()
