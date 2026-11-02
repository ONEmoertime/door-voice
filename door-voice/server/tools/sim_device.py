# -*- coding: utf-8 -*-
"""模拟设备：在 PC 上扮演 ESP32，验证「云端理解 → 签名指令 → 设备校验 → 回执」全链路。

硬件还没接上时先用它，把云端调通；等板子到了，固件的行为应当与这里一致。

用法：
    python tools/sim_device.py --text "帮我开一下门"
    python tools/sim_device.py --text "别开门"          # 应该收到 reply 而不是 command
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")


def verify_command(secret: str, cmd: dict) -> tuple[bool, str]:
    """与 firmware/main/secure.c、server/app/protocol.py 三处必须一致。"""
    try:
        action, door = cmd["action"], cmd["door"]
        nonce, ts, ttl = cmd["nonce"], int(cmd["ts"]), int(cmd.get("ttl", 5000))
        sig = cmd["sig"]
    except (KeyError, TypeError, ValueError):
        return False, "malformed"

    if action not in {"unlock", "lock", "query"}:
        return False, "action_not_allowed"
    if abs(time.time() - ts) > ttl / 1000:
        return False, "expired"

    msg = f"{action}|{door}|{nonce}|{ts}".encode()
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False, "bad_signature"
    return True, "ok"


async def run(args: argparse.Namespace) -> int:
    try:
        import websockets
    except ImportError:
        print("缺少 websockets：pip install -r requirements.txt（uvicorn[standard] 已包含）")
        return 2

    uri = f"{args.url}/ws/{args.device}?token={args.token}"
    print(f"连接 {uri}")
    ok_count = 0

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "hello", "device_id": args.device, "fw": "sim-0.1"}))
        print(f"发送文本：{args.text}")
        await ws.send(json.dumps({"type": "text", "text": args.text}))

        deadline = time.time() + args.timeout
        while time.time() < deadline:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=max(0.5, deadline - time.time()))
            except asyncio.TimeoutError:
                break

            if isinstance(message, bytes):
                print(f"  ← 收到音频 {len(message)} 字节（TTS）")
                continue

            data = json.loads(message)
            kind = data.get("type")
            if kind == "command":
                ok, reason = verify_command(args.secret, data)
                print(f"  ← 指令 {data.get('action')} / {data.get('cmd_id')} → 校验 {reason}")
                if ok:
                    ok_count += 1
                    await ws.send(
                        json.dumps(
                            {"type": "ack", "cmd_id": data.get("cmd_id"), "result": "ok", "latency_ms": 12}
                        )
                    )
            elif kind == "reply":
                print(f"  ← 回复：{data.get('text')}")
            else:
                print(f"  ← {json.dumps(data, ensure_ascii=False)}")

    print(f"\n完成：收到并校验通过 {ok_count} 条指令")
    return 0 if ok_count or args.text == "" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="模拟 ESP32 设备")
    parser.add_argument("--url", default="ws://127.0.0.1:8000")
    parser.add_argument("--device", default="esp32-01")
    parser.add_argument("--token", default="dev-secret-change-me")
    parser.add_argument("--secret", default="dev-secret-change-me")
    parser.add_argument("--text", default="帮我开一下门")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
