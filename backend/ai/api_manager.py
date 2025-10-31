"""
AI API 管理：统一封装不同大模型调用，优先使用 DeepSeek。
"""

from __future__ import annotations

from typing import Any, Dict, List

from api_clients.deepseek_client.client import DeepSeekClient


class AIAPIManager:
    def __init__(self, deepseek: DeepSeekClient | None = None):
        self.deepseek = deepseek

    def generate_insight(self, request: Dict[str, Any]) -> Dict[str, Any]:
        messages: List[Dict[str, str]] = request.get("messages", [])
        # 优先 DeepSeek
        if self.deepseek is not None and messages:
            try:
                resp = self.deepseek.generate(messages=messages)
                # 规范化输出
                content = ""
                try:
                    content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                except Exception:
                    content = str(resp)
                return {
                    "ok": True,
                    "provider": "deepseek",
                    "input": {"messages": messages},
                    "raw": resp,
                    "output": {
                        "summary": content,
                        "confidence": 0.5,
                    },
                }
            except Exception as e:
                return {
                    "ok": False,
                    "provider": "deepseek",
                    "error": str(e),
                }

        # 回退 mock
        return {
            "ok": True,
            "provider": "mock",
            "input": request,
            "output": {
                "summary": "占位洞察：请接入真实模型以获得更优建议",
                "confidence": 0.1,
            },
        }


