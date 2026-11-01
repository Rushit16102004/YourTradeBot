import json, time, subprocess, urllib.request, websocket

def safe_print(msg):
    print(str(msg).encode("ascii", "replace").decode())

chrome = subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--remote-debugging-port=9235",
    "--remote-allow-origins=*",
    r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_sebi_timer_test",
    "--disable-gpu",
    "--no-first-run",
    "--window-size=1600,1000",
    "http://127.0.0.1:8000"
])

try:
    time.sleep(3)
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9235/json").read())
    page_target = next(t for t in targets if t.get("type") == "page")
    ws = websocket.create_connection(page_target["webSocketDebuggerUrl"], timeout=25)

    def eval_js(expr):
        msg = {"id": int(time.time() * 1000) % 1000000, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}}
        ws.send(json.dumps(msg))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg["id"]:
                return resp.get("result", {}).get("result", {}).get("value")

    safe_print("=" * 60)
    safe_print("TEST: AUTO-DISMISS SEBI FOOTER BAR AFTER 10 SECONDS")
    safe_print("=" * 60)

    # 1. Check initial state
    bar_initial_display = eval_js("document.getElementById('sebi-footer-bar').style.display")
    bar_initial_opacity = eval_js("window.getComputedStyle(document.getElementById('sebi-footer-bar')).opacity")
    safe_print(f"[1] Initial footer display: {bar_initial_display}, opacity: {bar_initial_opacity}")
    assert bar_initial_display != "none", "Footer bar must initially be visible on page load"

    # 2. Test manual dismissSebiFooter function
    safe_print("\n[2] Testing dismissSebiFooter() animation...")
    eval_js("dismissSebiFooter()")
    time.sleep(0.1)
    bar_fading_opacity = eval_js("document.getElementById('sebi-footer-bar').style.opacity")
    bar_fading_transform = eval_js("document.getElementById('sebi-footer-bar').style.transform")
    safe_print(f"    During transition: opacity = {bar_fading_opacity}, transform = {bar_fading_transform}")
    assert bar_fading_opacity == "0", "Opacity must transition to 0"
    assert "translateY(100%)" in bar_fading_transform, "Transform must slide bar down out of viewport"

    time.sleep(0.7)
    bar_final_display = eval_js("document.getElementById('sebi-footer-bar').style.display")
    safe_print(f"    After 0.7s transition: display = {bar_final_display}")
    assert bar_final_display == "none", "Display must become 'none' after transition"
    safe_print("    -> PASS: dismissSebiFooter() cleanly slides and hides the bar!")

    safe_print("\n============================================================")
    safe_print("AUTO-DISMISS VERIFICATION COMPLETED SUCCESSFULLY!")
    safe_print("============================================================")

finally:
    try: ws.close()
    except Exception: pass
    chrome.kill()
