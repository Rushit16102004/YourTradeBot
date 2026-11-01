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
    print("STARTING E2E VERIFICATION: CURSOR PRIORITY (1. Candle, 2. Drawing, 3. Indicator, 4. S&R)")
    print("=" * 60)

    chrome = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_priority_test",
        "--disable-gpu",
        "--no-first-run",
        "--window-size=1600,950",
        "http://127.0.0.1:8000"
    ])

    try:
        time.sleep(3)
        targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
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

        # 1. Login as Admin
        eval_js("""
            fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: 'admin', password: '123@Qweasd'})
            }).then(r => r.json()).then(data => {
                if (data.token) {
                    localStorage.setItem('auth_token', data.token);
                    currentUser = data.user;
                    updateUserAuthUI();
                }
            });
        """)
        time.sleep(2)

        # 2. Check that chart and candles are loaded
        status = eval_js("""
            (() => {
                return {
                    candlesCount: activeCandles ? activeCandles.length : 0,
                    hasChart: !!chart,
                    hasCandleSeries: !!candleSeries,
                    hasOverlay: !!document.getElementById('drawing-overlay')
                };
            })()
        """)
        print("Initial Chart Status:", status)
        assert status and status["candlesCount"] > 0, "Candles not loaded!"

        # 3. Create a test Rectangle drawing box placed directly on top of the last 15 candles
        rect_info = eval_js("""
            (() => {
                const n = activeCandles.length;
                const cStart = activeCandles[n - 12];
                const cEnd = activeCandles[n - 2];
                
                // Find min low and max high across these candles
                const slice = activeCandles.slice(n - 12, n - 1);
                const minPrice = Math.min(...slice.map(c => c.low)) - 10;
                const maxPrice = Math.max(...slice.map(c => c.high)) + 40;

                const testBox = {
                    id: 'test_box_' + Date.now(),
                    type: 'rect',
                    time1: cStart.time,
                    price1: maxPrice,
                    time2: cEnd.time,
                    price2: minPrice,
                    color: '#ff9800',
                    remark: 'Priority Test Box Over Candles'
                };

                drawings.push(testBox);
                renderAllDrawings();
                
                // Target candle inside the box (candle at n - 6)
                const targetCandle = activeCandles[n - 6];
                const targetX = timeToX(targetCandle.time);
                const targetY = priceToY((targetCandle.high + targetCandle.low) / 2);

                const wrap = document.getElementById('main-chart-wrapper').getBoundingClientRect();
                return {
                    boxId: testBox.id,
                    targetTime: targetCandle.time,
                    targetClientX: wrap.left + targetX,
                    targetClientY: wrap.top + targetY,
                    candleHigh: targetCandle.high,
                    candleLow: targetCandle.low,
                    boxMin: minPrice,
                    boxMax: maxPrice
                };
            })()
        """)
        print("Placed Test Rectangle Box Over Candles:", rect_info)

        # 4. Test Priority 1: Move cursor directly over the candle that is inside the box
        candle_hover_res = eval_js(f"""
            (() => {{
                const clientX = {rect_info['targetClientX']};
                const clientY = {rect_info['targetClientY']};

                // Trigger evaluateCursorPriority
                const evt = new MouseEvent('mousemove', {{
                    clientX: clientX,
                    clientY: clientY,
                    bubbles: true
                }});
                document.getElementById('main-chart-wrapper').dispatchEvent(evt);

                const candleHit = getCandleUnderCursor(clientX, clientY);
                const overlay = document.getElementById('drawing-overlay');
                const isCandlePriorityActive = overlay.classList.contains('candle-priority-active');
                const srTip = document.getElementById('sr-hover-tooltip');
                const isTooltipHidden = (!srTip || srTip.style.display === 'none');

                return {{
                    hasCandleHit: !!candleHit,
                    hitCandleTime: candleHit ? candleHit.candle.time : null,
                    isCandlePriorityActive: isCandlePriorityActive,
                    isTooltipHidden: isTooltipHidden
                }};
            }})()
        """)
        print("Priority 1: Candle Hover Result (Over Box):", candle_hover_res)
        assert candle_hover_res["hasCandleHit"], "Candle was not detected under cursor!"
        assert candle_hover_res["isCandlePriorityActive"], "candle-priority-active class was not added to overlay!"
        assert candle_hover_res["isTooltipHidden"], "Tooltips must be hidden when hovering a candle!"

        # 5. Test Priority 1 Click: Click the candle inside the box
        click_res = eval_js(f"""
            (() => {{
                const clientX = {rect_info['targetClientX']};
                const clientY = {rect_info['targetClientY']};

                // Simulate click on the candle through the box
                const wrap = document.getElementById('main-chart-wrapper').getBoundingClientRect();
                const x = clientX - wrap.left;
                const y = clientY - wrap.top;

                const candle = activeCandles.find(c => c.time === {rect_info['targetTime']});
                const sDataMap = new Map();
                sDataMap.set(candleSeries, candle);

                handleChartCandleClick({{
                    point: {{ x: x, y: y }},
                    time: {rect_info['targetTime']},
                    seriesData: sDataMap
                }});

                const aiPill = document.getElementById('ai-candle-pill');
                const shapePill = document.getElementById('shape-action-pill');

                return {{
                    aiPillDisplayed: (aiPill && aiPill.style.display !== 'none'),
                    shapePillDisplayed: (shapePill && shapePill.style.display !== 'none'),
                    selectedShapeId: selectedShapeId
                }};
            }})()
        """)
        print("Priority 1: Candle Click Result (Over Box):", click_res)
        assert click_res["aiPillDisplayed"], "Explain Candle with AI pill should be displayed on candle click!"
        assert not click_res["shapePillDisplayed"], "Shape action pill should NOT be displayed when clicking candle!"

        # 6. Test Priority 2: Move cursor outside candles, but inside the box
        box_hover_res = eval_js(f"""
            (() => {{
                // Find empty space 25 points above candle high, but still inside box (which is +40 above high)
                const wrap = document.getElementById('main-chart-wrapper').getBoundingClientRect();
                const emptyX = {rect_info['targetClientX']};
                const emptyY = wrap.top + priceToY({rect_info['candleHigh']} + 25);

                const evt = new MouseEvent('mousemove', {{
                    clientX: emptyX,
                    clientY: emptyY,
                    bubbles: true
                }});
                document.getElementById('main-chart-wrapper').dispatchEvent(evt);

                const candleHit = getCandleUnderCursor(emptyX, emptyY);
                const overlay = document.getElementById('drawing-overlay');
                const isCandlePriorityActive = overlay.classList.contains('candle-priority-active');
                
                const drawingHit = getDrawingUnderCursor(emptyX - wrap.left, emptyY - wrap.top);

                return {{
                    hasCandleHit: !!candleHit,
                    isCandlePriorityActive: isCandlePriorityActive,
                    hasDrawingHit: !!drawingHit,
                    drawingId: drawingHit ? drawingHit.id : null
                }};
            }})()
        """)
        print("Priority 2: Drawing Hover in Empty Space:", box_hover_res)
        assert not box_hover_res["hasCandleHit"], "Should not detect candle in open space 25 points above candle!"
        assert not box_hover_res["isCandlePriorityActive"], "candle-priority-active must be removed in open space!"
        assert box_hover_res["hasDrawingHit"], "Drawing must be detected under cursor in Priority 2!"

        take_screenshot("cursor_priority_candle_first_verified.png")
        print("\nALL CURSOR PRIORITY TESTS PASSED SUCCESSFULLY!")

    finally:
        try:
            ws.close()
        except Exception:
            pass
        chrome.kill()

if __name__ == "__main__":
    run()
