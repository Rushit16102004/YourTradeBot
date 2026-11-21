"""
tests/test_auth_and_security.py
Comprehensive automated test suite for authentication security, Bcrypt password hashing,
JWT token verification, Brute-Force lockout shield, and International Phone Number sanitization.
"""
import pytest
from database import user_db
from server import brute_force_shield, BruteForceShield


class TestPasswordSecurity:
    def test_bcrypt_hashing_and_verification(self):
        password = "SecurePassword123!"
        hashed = user_db.hash_password(password)
        assert hashed != password, "Password must not be stored in plain text"
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$"), "Must use bcrypt format"
        assert user_db.verify_password(password, hashed), "Valid password must verify"
        assert not user_db.verify_password("WrongPassword999", hashed), "Invalid password must fail"


class TestJWTTokenSecurity:
    def test_jwt_issuance_and_decoding(self):
        token = user_db.create_access_token(
            user_id="user_test_99",
            username="tester",
            role="trader",
            trading_style="intraday_scalper"
        )
        assert isinstance(token, str) and len(token) > 20
        payload = user_db.decode_access_token(token)
        assert payload is not None
        assert payload.get("sub") == "user_test_99"
        assert payload.get("username") == "tester"
        assert payload.get("role") == "trader"
        assert payload.get("trading_style") == "intraday_scalper"

    def test_invalid_jwt_token_rejection(self):
        assert user_db.decode_access_token("tampered.fake.token") is None
        assert user_db.decode_access_token("") is None


class TestBruteForceShield:
    def test_brute_force_lockout_trigger(self):
        shield = BruteForceShield(max_failures=5, lockout_seconds=900)
        test_user = "brute_target_user"
        test_ip = "192.168.10.55"

        # Initially unlocked
        locked, remaining = shield.is_locked(test_user, test_ip)
        assert not locked
        assert remaining == 0

        # 4 consecutive failures should not lock yet
        for i in range(4):
            is_locked, _ = shield.record_failure(test_user, test_ip)
            assert not is_locked

        # 5th failure must trigger lockout
        is_locked, lock_seconds = shield.record_failure(test_user, test_ip)
        assert is_locked, "5th failure must trigger lockout"
        assert lock_seconds >= 890

        # Subsequent check confirms locked
        locked, remaining = shield.is_locked(test_user, test_ip)
        assert locked
        assert remaining > 0

        # Success clears lockout
        shield.record_success(test_user, test_ip)
        locked, _ = shield.is_locked(test_user, test_ip)
        assert not locked, "Successful authentication must clear lockout"


class TestInternationalPhoneSanitization:
    def test_indian_phone_validation(self):
        valid_nums = ["9876543210", "8160034453", "7000112233", "6999887766"]
        for num in valid_nums:
            is_valid, full_e164, local_digits, msg = user_db.sanitize_phone_number(num, country_code="+91")
            assert is_valid, f"Expected {num} to be valid: {msg}"
            assert full_e164 == f"+91 {num}"
            assert local_digits == num

        # Invalid Indian numbers (starting with wrong digit or wrong length)
        invalid_nums = ["1234567890", "5555555555", "98765", "987654321000"]
        for num in invalid_nums:
            is_valid, _, _, _ = user_db.sanitize_phone_number(num, country_code="+91")
            assert not is_valid, f"Expected {num} to be rejected"

    def test_international_phone_validation(self):
        # Valid US/Canada (+1)
        is_valid, full_e164, local_digits, _ = user_db.sanitize_phone_number("4155552671", country_code="+1")
        assert is_valid
        assert full_e164 == "+1 4155552671"
        assert local_digits == "4155552671"

        # Valid UK (+44)
        is_valid, full_e164, local_digits, _ = user_db.sanitize_phone_number("7911123456", country_code="+44")
        assert is_valid
        assert full_e164 == "+44 7911123456"

        # Valid UAE (+971)
        is_valid, full_e164, local_digits, _ = user_db.sanitize_phone_number("501234567", country_code="+971")
        assert is_valid
        assert full_e164 == "+971 501234567"

        # Invalid short international number
        is_valid, _, _, _ = user_db.sanitize_phone_number("123", country_code="+1")
        assert not is_valid
