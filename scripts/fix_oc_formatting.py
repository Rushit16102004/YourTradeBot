import os

path = os.path.join("RAG", "llm_client.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old_chunk = """            # Institutional Intelligence: Option Chain & PCR
            oc = market_state.get("option_chain", {})
            oc_str = ""
            if oc:
                oc_str = (
                    f"DERIVATIVES & LIVE OPTION CHAIN CONFLUENCE (PCR & MAX OI):\\n"
                    f"• Put-Call Ratio (PCR): {oc.get('pcr')} ({oc.get('pcr_bias_badge')} - {oc.get('pcr_bias_text')})\\n"
                    f"• Institutional Range: {oc.get('institutional_range')}\\n"
                    f"• Max Call OI (Resistance Ceiling): ₹{oc.get('max_call_oi_strike')} ({oc.get('max_call_oi_distance_pts'):+} pts away)\\n"
                    f"• Max Put OI (Support Floor): ₹{oc.get('max_put_oi_strike')} ({oc.get('max_put_oi_distance_pts'):+} pts away)\\n"
                    f"• Active OI Flow: {oc.get('oi_action')}\\n\\n"
                )"""

new_chunk = """            # Institutional Intelligence: Option Chain & PCR
            oc = market_state.get("option_chain", {})
            oc_str = ""
            if oc:
                c_dist = float(oc.get("max_call_oi_distance_pts") or 0.0)
                p_dist = float(oc.get("max_put_oi_distance_pts") or 0.0)
                oc_str = (
                    f"DERIVATIVES & LIVE OPTION CHAIN CONFLUENCE (PCR & MAX OI):\\n"
                    f"• Put-Call Ratio (PCR): {oc.get('pcr', 1.0)} ({oc.get('pcr_bias_badge', 'Neutral')} - {oc.get('pcr_bias_text', 'Balanced')})\\n"
                    f"• Institutional Range: {oc.get('institutional_range', '--')}\\n"
                    f"• Max Call OI (Resistance Ceiling): ₹{oc.get('max_call_oi_strike', '--')} ({c_dist:+} pts away)\\n"
                    f"• Max Put OI (Support Floor): ₹{oc.get('max_put_oi_strike', '--')} ({p_dist:+} pts away)\\n"
                    f"• Active OI Flow: {oc.get('oi_action', 'Balanced')}\\n\\n"
                )"""

if old_chunk in text:
    text = text.replace(old_chunk, new_chunk, 1)
    print("Replaced oc_str with safe float formatting.")
else:
    print("old_chunk not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated RAG/llm_client.py")
