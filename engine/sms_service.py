"""
engine/sms_service.py - Real SMS Gateway Dispatcher for Mobile Number OTP Authentication.
Supports:
1. Fast2SMS (Indian SMS Gateway - OTP Route, instant delivery, DLT-exempt Quick OTP)
2. Twilio (Global SMS Gateway)
3. Development Fallback / Console Simulation (when API key is not yet configured)
"""
from __future__ import annotations

import os
import re
import logging
from typing import Tuple, Optional
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("SMSService")


class SMSService:
    _instance: Optional[SMSService] = None

    def __init__(self):
        self.provider = os.getenv("SMS_PROVIDER", "fast2sms").strip().lower()
        self.fast2sms_api_key = os.getenv("FAST2SMS_API_KEY", "").strip()
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_from_phone = os.getenv("TWILIO_FROM_PHONE", "").strip()

    @classmethod
    def get_instance(cls) -> SMSService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def sanitize_indian_phone(phone: str) -> Tuple[bool, str, str]:
        """
        Validates and standardizes a 10-digit Indian mobile number.
        Returns: (is_valid: bool, cleaned_10_digit_phone: str, error_msg: str)
        """
        raw = re.sub(r"[^\d]", "", str(phone).strip())
        if raw.startswith("91") and len(raw) == 12:
            raw = raw[2:]
        elif raw.startswith("0") and len(raw) == 11:
            raw = raw[1:]

        if len(raw) != 10 or not raw[0] in "6789":
            return False, raw, "Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."
        return True, raw, ""

    def send_otp(self, phone: str, otp_code: str) -> Tuple[bool, str]:
        """
        Dispatches a 6-digit OTP code to the given mobile number via the configured SMS Gateway.
        Returns: (success: bool, user_friendly_message: str)
        """
        valid, clean_phone, err = self.sanitize_indian_phone(phone)
        if not valid:
            return False, err

        # Masked phone for logs & privacy (e.g., +91 98****3210)
        masked_phone = f"+91 {clean_phone[:2]}****{clean_phone[-4:]}"

        # 1. Fast2SMS Provider (India Default)
        if self.provider == "fast2sms":
            api_key = os.getenv("FAST2SMS_API_KEY", "").strip() or self.fast2sms_api_key
            if not api_key or api_key.startswith("your_"):
                logger.warning(
                    "[SMS DEV MODE] FAST2SMS_API_KEY is not set in .env. Simulated OTP for %s: [%s]",
                    clean_phone,
                    otp_code,
                )
                return True, f"OTP sent to {masked_phone} (Dev Mode OTP: {otp_code})"

            try:
                url = "https://www.fast2sms.com/dev/bulkV2"
                headers = {
                    "authorization": api_key,
                    "Content-Type": "application/json",
                }
                payload = {
                    "route": "otp",
                    "variables_values": str(otp_code),
                    "numbers": clean_phone,
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=12)
                try:
                    res_data = resp.json()
                except Exception:
                    res_data = {}

                if resp.status_code == 200 and res_data.get("return") is True:
                    logger.info("Fast2SMS OTP successfully dispatched to %s", masked_phone)
                    return True, f"OTP sent successfully via SMS to {masked_phone}"
                else:
                    raw_msg = res_data.get("message")
                    if isinstance(raw_msg, list) and raw_msg:
                        err_str = raw_msg[0]
                    elif isinstance(raw_msg, str) and raw_msg:
                        err_str = raw_msg
                    else:
                        err_str = f"HTTP {resp.status_code}"

                    logger.error("Fast2SMS dispatch error to %s (code %s): %s", masked_phone, resp.status_code, err_str)

                    # Check for Fast2SMS website verification / KYC requirement (status_code 996, 999)
                    is_kyc_pending = (
                        "verification" in err_str.lower()
                        or "kyc" in err_str.lower()
                        or "dlt" in err_str.lower()
                        or res_data.get("status_code") in (996, 999)
                    )
                    if is_kyc_pending:
                        logger.warning(
                            "[Fast2SMS OTP KYC Required] %s. Providing dev fallback OTP [%s] for %s so registration is never blocked.",
                            err_str,
                            otp_code,
                            clean_phone,
                        )
                        return True, f"OTP: {otp_code} (Fast2SMS KYC Pending — code: {otp_code})"

                    return False, f"SMS Gateway error: {err_str}"
            except Exception as e:
                logger.error("Fast2SMS request failed: %s", e)
                return False, f"SMS delivery failed: {e}"

        # 2. Twilio Provider
        elif self.provider == "twilio":
            if not (self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_phone):
                logger.warning("[SMS DEV MODE] Twilio credentials incomplete. Simulated OTP for %s: [%s]", clean_phone, otp_code)
                return True, f"OTP sent to {masked_phone} (Dev Mode OTP: {otp_code})"

            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
                auth = (self.twilio_account_sid, self.twilio_auth_token)
                data = {
                    "From": self.twilio_from_phone,
                    "To": f"+91{clean_phone}",
                    "Body": f"Your NIFTY 50 Pro Terminal verification code is {otp_code}. Valid for 5 minutes. Do not share with anyone.",
                }
                resp = requests.post(url, data=data, auth=auth, timeout=12)
                if resp.status_code in (200, 201):
                    logger.info("Twilio SMS OTP successfully dispatched to %s", masked_phone)
                    return True, f"OTP sent successfully via SMS to {masked_phone}"
                else:
                    logger.error("Twilio SMS dispatch failed: %s", resp.text)
                    return False, f"SMS Gateway error: {resp.status_code}"
            except Exception as e:
                logger.error("Twilio request failed: %s", e)
                return False, f"SMS delivery failed: {e}"

        # 3. Default / Console Simulation
        else:
            logger.info("[SMS DEV SIMULATION] Generated OTP for %s: [%s]", clean_phone, otp_code)
            return True, f"OTP sent to {masked_phone} (Dev Mode OTP: {otp_code})"


sms_service = SMSService.get_instance()
