"""音频处理：能量 VAD + PCM/WAV 工具（不依赖 numpy）。"""
from __future__ import annotations

import array
import io
import math
import wave
from dataclasses import dataclass, field

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16 bit


def rms(pcm: bytes) -> float:
    """16bit 单声道 PCM 的归一化 RMS（0~1）。"""
    if len(pcm) < 2:
        return 0.0
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    if not samples:
        return 0.0
    total = sum(s * s for s in samples)
    return math.sqrt(total / len(samples)) / 32768.0


@dataclass
class VAD:
    """简单能量 VAD：连续静音超过阈值即认为一句话结束。

    真实项目可换 silero-vad 或 ESP32 侧上行的 VAD 事件；
    这里保持零依赖，保证服务端在没装模型的机器上也能跑通链路。
    """

    threshold: float = 0.018
    silence_ms: int = 600
    max_utterance_ms: int = 12000
    frame_ms: int = 20
    _buffer: bytearray = field(default_factory=bytearray)
    _speaking: bool = False
    _silence_ms: int = 0
    _voiced_ms: int = 0

    def feed(self, pcm: bytes) -> bytes | None:
        """喂一帧；返回完整一句话的 PCM（未结束时返回 None）。"""
        level = rms(pcm)
        self._buffer.extend(pcm)
        self._voiced_ms += self.frame_ms

        if level >= self.threshold:
            self._speaking = True
            self._silence_ms = 0
        elif self._speaking:
            self._silence_ms += self.frame_ms

        ended = self._speaking and self._silence_ms >= self.silence_ms
        too_long = self._voiced_ms >= self.max_utterance_ms
        if ended or too_long:
            audio = bytes(self._buffer)
            self.reset()
            return audio if len(audio) > 1600 else None  # 太短（<50ms）丢弃
        return None

    def reset(self) -> None:
        self._buffer = bytearray()
        self._speaking = False
        self._silence_ms = 0
        self._voiced_ms = 0


def pcm_to_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()
