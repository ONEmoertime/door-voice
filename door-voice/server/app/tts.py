"""TTS：edge-tts 封装；未安装或失败时返回 None，改为文本回复。"""
from __future__ import annotations

import asyncio


class TTS:
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural") -> None:
        self.voice = voice
        self.available = False
        try:
            import edge_tts  # noqa: F401

            self.available = True
        except Exception:  # noqa: BLE001
            self.available = False

    async def synthesize(self, text: str) -> bytes | None:
        if not self.available or not text:
            return None
        import edge_tts

        try:
            communicate = edge_tts.Communicate(text, self.voice)
            chunks = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.extend(chunk["data"])
            return bytes(chunks) or None
        except Exception:  # noqa: BLE001
            return None


async def synth_blocking(tts: TTS, text: str) -> bytes | None:
    """在事件循环里跑，但把阻塞部分丢给线程池。"""
    return await asyncio.to_thread(lambda: asyncio.run(tts.synthesize(text)))
