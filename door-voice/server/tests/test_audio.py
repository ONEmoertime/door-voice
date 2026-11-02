"""VAD 与音频工具单测（纯标准库）。"""
from __future__ import annotations

import math
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.audio import VAD, pcm_to_wav, rms  # noqa: E402


def tone(freq: float, ms: int, amp: float = 0.3, sr: int = 16000) -> bytes:
    n = int(sr * ms / 1000)
    return b"".join(
        struct.pack("<h", int(32767 * amp * math.sin(2 * math.pi * freq * i / sr))) for i in range(n)
    )


def silence(ms: int, sr: int = 16000) -> bytes:
    return b"\x00\x00" * int(sr * ms / 1000)


class TestRMS(unittest.TestCase):
    def test_silence_is_zero(self):
        self.assertAlmostEqual(rms(silence(100)), 0.0, places=4)

    def test_tone_is_louder(self):
        self.assertGreater(rms(tone(440, 100)), 0.1)

    def test_short_buffer(self):
        self.assertEqual(rms(b""), 0.0)


class TestVAD(unittest.TestCase):
    def test_detects_end_of_speech(self):
        vad = VAD(threshold=0.02, silence_ms=100, max_utterance_ms=5000, frame_ms=20)
        result = None
        for _ in range(5):
            result = vad.feed(tone(440, 20))
        for _ in range(10):
            result = vad.feed(silence(20)) or result
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 1600)

    def test_silence_only_returns_none(self):
        vad = VAD(threshold=0.02, silence_ms=100, frame_ms=20)
        for _ in range(20):
            self.assertIsNone(vad.feed(silence(20)))


class TestWav(unittest.TestCase):
    def test_wav_header(self):
        data = pcm_to_wav(tone(440, 100))
        self.assertTrue(data.startswith(b"RIFF"))
        self.assertIn(b"WAVE", data[:20])


if __name__ == "__main__":
    unittest.main()
