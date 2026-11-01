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
    "--remote-debugging-port=9238",
    "--remote-allow-origins=*",
    r"--user-data-dir=C:\Users\ASUS\AppData\Local\Temp\chrome_terms_test",
    "--disable-gpu",
    "--no-first-run",
    "--window-size=1600,1000",
    "http://127.0.0.1:8000"
])

try:
    time.sleep(3)
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9238/json").read())
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

    safe_print("=" * 70)
    safe_print("STARTING E2E VERIFICATION: COMPREHENSIVE TERMS, DISCLAIMER & PRIVACY POLICY")
    safe_print("=" * 70)

    # 1. Open the SEBI / Terms Modal
    safe_print("[1] Opening SEBI / Terms Modal...")
    eval_js("openSebiModal()")
    time.sleep(0.5)

    modal_disp = eval_js("document.getElementById('sebi-modal-overlay').style.display")
    safe_print(f"    Modal display: {modal_disp}")
    assert modal_disp == "flex", "Modal must be visible with display: flex"

    # 2. Check Primary Charting & Analytics Software notice
    modal_text = eval_js("document.getElementById('sebi-modal-overlay').textContent")
    safe_print("\n[2] Checking Primary Notice...")
    has_charting_notice = "CHARTING & COMPUTATIONAL ANALYTICS SOFTWARE" in modal_text and "NOT provide investment advice" in modal_text
    safe_print(f"    Primary notice ('CHARTING & COMPUTATIONAL ANALYTICS SOFTWARE, NOT investment advice'): {has_charting_notice}")
    assert has_charting_notice is True, "Must prominently state charting/analytics software not investment advice"
    safe_print("    -> PASS: Primary Notice verified!")

    # 3. Check All 10 Clauses
    safe_print("\n[3] Checking all 10 Legal & Operational clauses...")
    clauses = [
        "1. Charting & Analytics Software Only",
        "2. Broker Interface Priority",
        "3. Independent Verification of Signals",
        "4. User Parameters, Sizing, Leverage & No Automated Bailout Guarantee",
        "5. Market Data Accuracy, Delays, Historical Feeds & Provider Limits",
        "6. Service Availability, Maintenance, Outages & Force Majeure",
        "7. AI Strategy Copilot & Developer Communication Disclaimer",
        "8. Privacy Policy & AI Model Training Data Usage",
        "9. Capital Risk Disclosure & User Risk Allocation",
        "10. Complete Developer Immunity, Indemnification & Limitation of Liability"
    ]
    for c in clauses:
        found = c in modal_text
        safe_print(f"    - Clause '{c}': {found}")
        assert found is True, f"Clause '{c}' must be present in modal text!"
    safe_print("    -> PASS: All 10 clauses present and verified!")

    # 4. Check Registration Checkbox Agreement
    safe_print("\n[4] Checking Registration Form Checkbox text...")
    reg_label = eval_js("document.querySelector('label[for=\"reg-accept-policy\"]').textContent")
    has_reg_charting_notice = "Charting/Analytics Software, NOT Investment Advice" in reg_label
    has_reg_model_train = "model training purposes" in reg_label
    safe_print(f"    Registration label contains 'Charting/Analytics Software, NOT Investment Advice': {has_reg_charting_notice}")
    safe_print(f"    Registration label contains model training disclosure: {has_reg_model_train}")
    assert has_reg_charting_notice and has_reg_model_train, "Registration label must explicitly mention charting/analytics only and model training"
    safe_print("    -> PASS: Registration agreement text verified!")

    # 5. Capture Screenshot of Opened Modal
    take_screenshot("comprehensive_terms_and_policy_modal.png")

    safe_print("\n=======================================================================")
    safe_print("ALL COMPREHENSIVE TERMS, DISCLAIMER & POLICY CHECKS PASSED!")
    safe_print("=======================================================================")

finally:
    try: ws.close()
    except Exception: pass
    chrome.kill()
