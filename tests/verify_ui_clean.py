import base64
import json
import subprocess
import time
import urllib.request
import websocket
from pathlib import Path

ARTIFACT_DIR = Path(r"C:\Users\ASUS\.gemini\antigravity\brain\a35c8187-b54e-4a01-9b33-c17b3968fd99")

def run():
    print("Verifying UI clean without AI Journal...")
    chrome = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_clean_test",
        "--disable-gpu",
        "--no-first-run",
        "--window-size=1600,950",
        "http://127.0.0.1:8000"
    ])

    try:
        time.sleep(3)
        targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
        page_target = next(t for t in targets if t.get("type") == "page")
        ws = websocket.create_connection(page_target["webSocketDebuggerUrl"], timeout=10)

        def cdp_send(method, params=None):
            nonlocal msg_id
            msg_id += 1
            payload = {"id": msg_id, "method": method}
            if params:
                payload["params"] = params
            ws.send(json.dumps(payload))
            while True:
                resp = json.loads(ws.recv())
                if resp.get("id") == msg_id:
                    return resp.get("result", {})

        msg_id = 0
        cdp_send("Page.enable")
        cdp_send("Runtime.enable")
        time.sleep(2)

        # Check DOM elements
        eval_res = cdp_send("Runtime.evaluate", {
            "expression": """
                ({
                    hasJournalBtn: !!document.getElementById('btn-prediction-journal'),
                    hasJournalModal: !!document.getElementById('prediction-journal-modal'),
                    hasHistoryBtn: !!document.querySelector("button[onclick='openSignalHistoryModal()']"),
                    hasSyncBtn: !!document.querySelector("button[onclick='fetchData(true)']"),
                    hasLoginBtn: !!document.getElementById('btn-guest-login'),
                })
            """,
            "returnByValue": True
        })
        dom_status = eval_res.get("result", {}).get("value", {})
        print("DOM Status:", dom_status)

        assert not dom_status["hasJournalBtn"], "btn-prediction-journal still exists in DOM!"
        assert not dom_status["hasJournalModal"], "prediction-journal-modal still exists in DOM!"
        assert dom_status["hasHistoryBtn"], "History button missing!"
        assert dom_status["hasSyncBtn"], "Sync button missing!"
        assert dom_status["hasLoginBtn"], "Login button missing!"

        # Take screenshot of clean navbar
        ss_res = cdp_send("Page.captureScreenshot", {"format": "png"})
        img_bytes = base64.b64decode(ss_res.get("data", ""))
        ss_path = ARTIFACT_DIR / "ai_journal_removed_user_display_clean.png"
        with open(ss_path, "wb") as f:
            f.write(img_bytes)
        print(f"Saved screenshot: {ss_path.name}")
        print("All UI checks PASSED! AI Journal is completely removed from user display.")

        ws.close()
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=2)
        except Exception:
            chrome.kill()

if __name__ == "__main__":
    run()
