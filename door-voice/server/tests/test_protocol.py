"""协议层单测：签名、过期、重放、白名单（纯标准库，无需装任何依赖）。

运行：python -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.protocol import (  # noqa: E402
    NonceCache,
    build_command,
    canonical,
    sign,
    verify_command,
)

SECRET = "dev-secret-change-me"
NOW = 1_762_000_000.0


class TestSign(unittest.TestCase):
    def test_sign_is_deterministic(self):
        a = sign(SECRET, "unlock", "front", "abc123", 1762000000)
        b = sign(SECRET, "unlock", "front", "abc123", 1762000000)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_canonical_field_order(self):
        self.assertEqual(canonical("unlock", "front", "n1", 123), "unlock|front|n1|123")

    def test_different_secret_differs(self):
        a = sign("s1", "unlock", "front", "n", 1)
        b = sign("s2", "unlock", "front", "n", 1)
        self.assertNotEqual(a, b)


class TestVerify(unittest.TestCase):
    def test_valid_command_passes(self):
        cmd = build_command(SECRET, "unlock", "front", now=NOW)
        self.assertTrue(verify_command(SECRET, cmd, now=NOW).ok)

    def test_tampered_action_fails(self):
        cmd = build_command(SECRET, "lock", "front", now=NOW)
        cmd["action"] = "unlock"
        result = verify_command(SECRET, cmd, now=NOW)
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "bad_signature")

    def test_expired_fails(self):
        cmd = build_command(SECRET, "unlock", "front", ttl=5000, now=NOW)
        self.assertFalse(verify_command(SECRET, cmd, now=NOW + 10).ok)

    def test_wrong_secret_fails(self):
        cmd = build_command(SECRET, "unlock", "front", now=NOW)
        self.assertFalse(verify_command("other", cmd, now=NOW).ok)

    def test_disallowed_action_rejected(self):
        cmd = build_command(SECRET, "unlock", "front", now=NOW)
        cmd["action"] = "delete_all"
        self.assertEqual(verify_command(SECRET, cmd, now=NOW).reason, "action_not_allowed")

    def test_missing_field_malformed(self):
        self.assertEqual(verify_command(SECRET, {"action": "unlock"}, now=NOW).reason, "malformed")


class TestReplay(unittest.TestCase):
    def test_replay_rejected(self):
        cache = NonceCache(ttl=60)
        cmd = build_command(SECRET, "unlock", "front", now=NOW)
        self.assertTrue(verify_command(SECRET, cmd, now=NOW, nonces=cache).ok)
        self.assertEqual(
            verify_command(SECRET, cmd, now=NOW, nonces=cache).reason, "replayed"
        )

    def test_new_command_still_passes(self):
        cache = NonceCache(ttl=60)
        first = build_command(SECRET, "unlock", "front", now=NOW)
        second = build_command(SECRET, "unlock", "front", now=NOW)
        self.assertTrue(verify_command(SECRET, first, now=NOW, nonces=cache).ok)
        self.assertTrue(verify_command(SECRET, second, now=NOW, nonces=cache).ok)


if __name__ == "__main__":
    unittest.main()
