"""设备注册表与审计日志。"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Device:
    device_id: str
    websocket: Any
    firmware: str = ""
    connected_at: float = field(default_factory=time.time)


class Registry:
    """内存注册表：一设备一连接。生产环境可换 Redis 以支持多进程。"""

    def __init__(self) -> None:
        self._devices: dict[str, Device] = {}

    def add(self, device_id: str, websocket: Any, firmware: str = "") -> Device:
        device = Device(device_id=device_id, websocket=websocket, firmware=firmware)
        self._devices[device_id] = device
        return device

    def remove(self, device_id: str) -> None:
        self._devices.pop(device_id, None)

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def count(self) -> int:
        return len(self._devices)


class Audit:
    """每次指令落库：谁、何时、什么动作、结果。门锁项目必须可回溯。"""

    def __init__(self, db_path: str | Path) -> None:
        self.path = str(db_path)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    device_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    detail TEXT
                )
                """
            )

    def log(self, device_id: str, event: str, detail: dict | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit (ts, device_id, event, detail) VALUES (?, ?, ?, ?)",
                (time.time(), device_id, event, json.dumps(detail or {}, ensure_ascii=False)),
            )

    def recent(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, device_id, event, detail FROM audit ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
