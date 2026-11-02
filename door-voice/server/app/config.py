"""服务端配置：全部来自环境变量，缺省值保证 mock 模式可跑。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8000
    api_base: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    chat_model: str = "deepseek-chat"
    asr_model: str = "small"
    asr_language: str = "zh"
    vad_threshold: float = 0.018
    vad_silence_ms: int = 600
    max_utterance_ms: int = 12000
    device_tokens: dict[str, str] = field(default_factory=dict)
    audit_db: str = "audit.db"

    @property
    def mock_mode(self) -> bool:
        return not self.api_key or self.api_key.startswith("sk-xxxx")


def _parse_devices(raw: str) -> dict[str, str]:
    """格式：esp32-01:secret1,esp32-02:secret2"""
    devices: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        device_id, token = item.split(":", 1)
        devices[device_id.strip()] = token.strip()
    return devices


def load() -> Settings:
    _load_env(ROOT / ".env")
    return Settings(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        api_base=os.environ.get("API_BASE", "https://api.deepseek.com/v1"),
        api_key=os.environ.get("API_KEY", ""),
        chat_model=os.environ.get("CHAT_MODEL", "deepseek-chat"),
        asr_model=os.environ.get("ASR_MODEL", "small"),
        asr_language=os.environ.get("ASR_LANGUAGE", "zh"),
        vad_threshold=float(os.environ.get("VAD_THRESHOLD", "0.018")),
        vad_silence_ms=int(os.environ.get("VAD_SILENCE_MS", "600")),
        max_utterance_ms=int(os.environ.get("MAX_UTTERANCE_MS", "12000")),
        device_tokens=_parse_devices(os.environ.get("DEVICE_TOKENS", "esp32-01:dev-secret-change-me")),
        audit_db=os.environ.get("AUDIT_DB", "audit.db"),
    )
