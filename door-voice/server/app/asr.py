"""ASR：faster-whisper 封装；未安装时返回 None，链路自动降级。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .audio import pcm_to_wav
from .config import Settings


class ASR:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self._model = None
        self.available = False
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(cfg.asr_model, device="cpu", compute_type="int8")
            self.available = True
        except Exception:  # noqa: BLE001  没装模型就降级，不影响服务启动
            self._model = None

    def transcribe(self, pcm: bytes) -> str | None:
        if not self._model or not pcm:
            return None
        wav_bytes = pcm_to_wav(pcm)
        tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
        try:
            tmp.write_bytes(wav_bytes)
            segments, _ = self._model.transcribe(
                str(tmp), language=self.cfg.asr_language, vad_filter=True
            )
            return "".join(seg.text for seg in segments).strip() or None
        except Exception:  # noqa: BLE001
            return None
        finally:
            tmp.unlink(missing_ok=True)
