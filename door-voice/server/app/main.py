"""FastAPI 入口：WebSocket 接入、VAD、ASR、Agent、TTS、指令下发。

启动：python -m app.main
没有 API Key / 没装模型时会进入 mock 模式：能跑通链路，便于先验证协议与硬件。
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .agent import Agent
from .asr import ASR
from .audio import VAD
from .config import load
from .devices import Audit, Registry
from .protocol import build_command
from .tts import TTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("door")

cfg = load()
registry = Registry()
audit = Audit(cfg.audit_db)
agent = Agent(cfg)
asr = ASR(cfg)
tts = TTS()

app = FastAPI(title="Door Voice Agent", version="0.1.0")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "mock_mode": cfg.mock_mode,
            "asr_ready": asr.available,
            "tts_ready": tts.available,
            "devices_online": registry.count(),
        }
    )


@app.get("/audit")
def audit_log(limit: int = 20) -> JSONResponse:
    return JSONResponse({"items": audit.recent(limit)})


async def handle_utterance(
    device_id: str, pcm: bytes, ws: WebSocket, text_hint: str | None = None
) -> None:
    started = time.perf_counter()
    if pcm:
        audit.log(device_id, "audio_received", {"bytes": len(pcm)})

    if text_hint is not None:
        text = text_hint
    else:
        text = await asyncio.to_thread(asr.transcribe, pcm)
    if not text:
        # mock 模式或 ASR 未就绪：让硬件先跑通“上传-回执”链路
        await ws.send_text(json.dumps({"type": "reply", "text": "（ASR 未就绪）", "audio": None}, ensure_ascii=False))
        audit.log(device_id, "asr_unavailable", {"bytes": len(pcm)})
        return

    audit.log(device_id, "asr", {"text": text})
    result = agent.handle(text)
    audit.log(device_id, "agent", {"text": text, "action": result.action, "source": result.source})

    secret = cfg.device_tokens[device_id]
    if result.action:
        command = build_command(secret, action=result.action, door=result.door)
        await ws.send_text(json.dumps(command, ensure_ascii=False))
        audit.log(device_id, "command_sent", {"cmd_id": command["cmd_id"], "action": result.action})

    audio = await tts.synthesize(result.reply)
    reply = {"type": "reply", "text": result.reply, "audio": "mp3" if audio else None}
    await ws.send_text(json.dumps(reply, ensure_ascii=False))
    if audio:
        await ws.send_bytes(audio)

    audit.log(device_id, "turn_done", {"ms": round((time.perf_counter() - started) * 1000)})


@app.websocket("/ws/{device_id}")
async def ws_endpoint(websocket: WebSocket, device_id: str, token: str = "") -> None:
    secret = cfg.device_tokens.get(device_id)
    if not secret or not token or not hmac.compare_digest(secret, token):
        await websocket.close(code=4401, reason="invalid token")
        audit.log(device_id, "auth_failed", {})
        return

    await websocket.accept()
    registry.add(device_id, websocket)
    audit.log(device_id, "connected", {})
    vad = VAD(threshold=cfg.vad_threshold, silence_ms=cfg.vad_silence_ms,
              max_utterance_ms=cfg.max_utterance_ms)

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            payload = message.get("bytes")
            if payload:
                utterance = vad.feed(payload)
                if utterance:
                    await handle_utterance(device_id, utterance, websocket)
                continue

            text = message.get("text")
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "hello":
                registry.get(device_id).firmware = str(data.get("fw", ""))
                await websocket.send_text(json.dumps({"type": "welcome", "device_id": device_id}))
            elif data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": int(time.time())}))
            elif data.get("type") == "ack":
                audit.log(device_id, "ack", data)
            elif data.get("type") == "text":
                # 调试用：跳过 ASR 直接注入一句文本，走 Agent 全链路。
                # 硬件还没接上时用它验证「理解 → 签名指令 → 回执」。
                audit.log(device_id, "text_injected", {"text": data.get("text", "")})
                await handle_utterance(device_id, b"", websocket, text_hint=data.get("text", ""))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        log.exception("ws error: %s", exc)
    finally:
        registry.remove(device_id)
        audit.log(device_id, "disconnected", {})


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host=cfg.host, port=cfg.port, reload=False)


if __name__ == "__main__":
    main()
