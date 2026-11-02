"""Agent：把一句话变成（回复, 动作）。

两条路径：
1. mock / 无 API Key：规则匹配，保证链路能跑通、能演示；
2. 有 API Key：走 function calling，由模型决定调哪个工具。

规则兜底不是“降级方案”，而是安全设计：门锁场景里，
关键词命中就执行比“等模型想 3 秒”更可靠。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import Settings

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "unlock_door",
            "description": "打开指定门锁。仅在用户明确要求开门时调用。",
            "parameters": {
                "type": "object",
                "properties": {"door": {"type": "string", "description": "门名称，默认 front"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lock_door",
            "description": "关闭门锁。",
            "parameters": {"type": "object", "properties": {"door": {"type": "string"}}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_status",
            "description": "查询门锁当前状态。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

UNLOCK_RE = re.compile(r"(开|打).{0,4}门|门.{0,3}(开|打)|开锁|让我进|unlock|open\s+the\s+door", re.IGNORECASE)
LOCK_RE = re.compile(r"(关|锁).{0,4}门|门.{0,3}(锁|关)|上锁|锁上|lock", re.IGNORECASE)
QUERY_RE = re.compile(r"状态|锁了吗|关了吗|在吗|查询|status", re.IGNORECASE)
# 否定优先：门锁场景里，“别开门”被识别成开门是安全事故
NEGATION_RE = re.compile(r"(不要|别|不用|无需|先别).{0,6}(开|打|unlock)", re.IGNORECASE)


@dataclass
class AgentResult:
    reply: str
    action: str | None = None
    door: str = "front"
    source: str = "rule"


class Agent:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self._client = None
        if not cfg.mock_mode:
            try:
                import httpx  # noqa: F401

                self._client = httpx.Client(
                    base_url=cfg.api_base.rstrip("/"),
                    headers={"Authorization": f"Bearer {cfg.api_key}"},
                    timeout=20,
                )
            except Exception:  # noqa: BLE001
                self._client = None

    def handle(self, text: str) -> AgentResult:
        text = (text or "").strip()
        if not text:
            return AgentResult("我没听清，请再说一次。")

        if self._client is not None:
            result = self._call_llm(text)
            if result is not None:
                return result

        return self._rule(text)

    # ---------- 规则兜底 ----------
    def _rule(self, text: str) -> AgentResult:
        if NEGATION_RE.search(text):
            return AgentResult("好的，不开门。")
        if UNLOCK_RE.search(text):
            return AgentResult("好的，正在为你开门。", action="unlock")
        if LOCK_RE.search(text):
            return AgentResult("好的，门已上锁。", action="lock")
        if QUERY_RE.search(text):
            return AgentResult("正在查询门锁状态。", action="query")
        return AgentResult("我听懂了这句话，但它不涉及门锁操作。可以说“开一下门”或“查询状态”。")

    # ---------- 模型路径 ----------
    def _call_llm(self, text: str) -> AgentResult | None:
        payload = {
            "model": self.cfg.chat_model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是门禁语音助手。用户要求开门/关门/查询状态时调用对应工具；"
                    "其他请求用一句话回应，不要调用工具。回复控制在 30 字以内。",
                },
                {"role": "user", "content": text},
            ],
            "tools": TOOLS,
            "temperature": 0.1,
        }
        try:
            resp = self._client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            choice = resp.json()["choices"][0]["message"]
        except Exception:  # noqa: BLE001
            return None

        calls = choice.get("tool_calls") or []
        if calls:
            fn = calls[0]["function"]
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            mapping = {"unlock_door": "unlock", "lock_door": "lock", "query_status": "query"}
            action = mapping.get(name)
            if action:
                return AgentResult(
                    choice.get("content") or "好的。",
                    action=action,
                    door=args.get("door", "front"),
                    source="llm",
                )
        content = choice.get("content")
        if content:
            return AgentResult(content.strip(), source="llm")
        return None
