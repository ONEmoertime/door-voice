"""Agent 规则路径单测（mock 模式，不需要 API Key 与网络）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent import Agent  # noqa: E402
from app.config import Settings  # noqa: E402


def mock_agent() -> Agent:
    cfg = Settings(api_key="")  # 空 key → mock 模式，只走规则
    return Agent(cfg)


class TestRules(unittest.TestCase):
    def test_unlock_variants(self):
        for text in ("开一下门", "帮我开个门", "把门打开", "unlock"):
            with self.subTest(text=text):
                self.assertEqual(mock_agent().handle(text).action, "unlock")

    def test_lock(self):
        self.assertEqual(mock_agent().handle("把门锁上").action, "lock")

    def test_query(self):
        self.assertEqual(mock_agent().handle("现在是什么状态").action, "query")

    def test_negation_blocks_unlock(self):
        for text in ("别开门", "不要打开门", "先别开门"):
            with self.subTest(text=text):
                self.assertIsNone(mock_agent().handle(text).action)

    def test_chitchat_has_no_action(self):
        self.assertIsNone(mock_agent().handle("今天天气不错").action)

    def test_empty_text(self):
        result = mock_agent().handle("   ")
        self.assertIsNone(result.action)
        self.assertIn("没听清", result.reply)


if __name__ == "__main__":
    unittest.main()
