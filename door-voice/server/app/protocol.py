"""指令签名与校验（纯标准库，方便单测和嵌入式侧对齐实现）。"""
from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass

DEFAULT_TTL_MS = 5000
ALLOWED_ACTIONS = {"unlock", "lock", "query"}


def _secret_bytes(secret: str | bytes) -> bytes:
    return secret.encode("utf-8") if isinstance(secret, str) else secret


def canonical(action: str, door: str, nonce: str, ts: int) -> str:
    """签名原文，客户端与设备必须完全一致，顺序不能改。"""
    return f"{action}|{door}|{nonce}|{ts}"


def sign(secret: str | bytes, action: str, door: str, nonce: str, ts: int) -> str:
    msg = canonical(action, door, nonce, ts).encode("utf-8")
    return hmac.new(_secret_bytes(secret), msg, hashlib.sha256).hexdigest()


def build_command(
    secret: str | bytes,
    action: str = "unlock",
    door: str = "front",
    ttl: int = DEFAULT_TTL_MS,
    now: float | None = None,
) -> dict:
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"不支持的 action：{action}")
    ts = int(now if now is not None else time.time())
    nonce = uuid.uuid4().hex[:8]
    return {
        "type": "command",
        "cmd_id": f"c-{uuid.uuid4().hex[:6]}",
        "action": action,
        "door": door,
        "nonce": nonce,
        "ts": ts,
        "ttl": ttl,
        "sig": sign(secret, action, door, nonce, ts),
    }


@dataclass
class VerifyResult:
    ok: bool
    reason: str = ""


class NonceCache:
    """设备侧重放防护；服务端只负责生成，校验在设备上。"""

    def __init__(self, ttl: int = 60) -> None:
        self.ttl = ttl
        self._seen: dict[str, float] = {}

    def check_and_add(self, nonce: str, now: float) -> bool:
        """返回 True 表示首次出现（可用），False 表示重复。"""
        self._evict(now)
        if nonce in self._seen:
            return False
        self._seen[nonce] = now
        return True

    def _evict(self, now: float) -> None:
        expired = [n for n, t in self._seen.items() if now - t > self.ttl]
        for n in expired:
            self._seen.pop(n, None)


def verify_command(
    secret: str | bytes,
    payload: dict,
    now: float | None = None,
    nonces: NonceCache | None = None,
) -> VerifyResult:
    """设备侧校验逻辑：TTL → 签名 → 重放 → 白名单。"""
    now = now if now is not None else time.time()
    action = payload.get("action", "")
    if action not in ALLOWED_ACTIONS:
        return VerifyResult(False, "action_not_allowed")

    try:
        ts = int(payload["ts"])
        ttl = int(payload.get("ttl", DEFAULT_TTL_MS))
        nonce = str(payload["nonce"])
        door = str(payload["door"])
        sig = str(payload["sig"])
    except (KeyError, TypeError, ValueError):
        return VerifyResult(False, "malformed")

    if abs(now - ts) > ttl / 1000:
        return VerifyResult(False, "expired")

    expected = sign(secret, action, door, nonce, ts)
    if not hmac.compare_digest(expected, sig):
        return VerifyResult(False, "bad_signature")

    if nonces is not None and not nonces.check_and_add(nonce, now):
        return VerifyResult(False, "replayed")

    return VerifyResult(True)
