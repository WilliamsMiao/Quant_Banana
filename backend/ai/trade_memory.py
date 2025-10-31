from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class TradeEntry:
    id: str
    created_at: str
    symbol: str
    action: str
    reason: str
    ai_output: Dict[str, Any]
    ai_input: Dict[str, Any]
    targets: Dict[str, Any] = field(default_factory=dict)  # {stop_loss, take_profit, timeframe, size}
    status: str = "open"  # open|closed
    last_check: Optional[str] = None
    reflections: List[Dict[str, Any]] = field(default_factory=list)


class TradeMemory:
    def __init__(self, storage_path: str = "data/trade_journal.jsonl"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

    def append(self, entry: TradeEntry) -> None:
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def load_all(self) -> List[TradeEntry]:
        if not os.path.exists(self.storage_path):
            return []
        items: List[TradeEntry] = []
        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                items.append(TradeEntry(**d))
        return items

    def rewrite(self, entries: List[TradeEntry]) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")

    def record_ai_decision(self, ai_event: Dict[str, Any]) -> TradeEntry:
        from uuid import uuid4
        now = datetime.now().isoformat()
        data = ai_event.get("data", {})
        ai_out = data.get("ai", {})
        ai_input = data.get("ai_input", {})
        symbol = str(data.get("symbol", ""))
        action = str(data.get("strategy_action", ""))
        reason = str(ai_input.get("reason") or data.get("reason") or "")
        targets = self._extract_targets(ai_out)
        entry = TradeEntry(
            id=str(uuid4()),
            created_at=now,
            symbol=symbol,
            action=action,
            reason=reason,
            ai_output=ai_out,
            ai_input=ai_input,
            targets=targets,
        )
        self.append(entry)
        return entry

    def refresh_progress(self, get_price, reflection_cb=None) -> None:
        entries = self.load_all()
        changed = False
        for e in entries:
            if e.status != "open":
                continue
            price = None
            try:
                price = float(get_price(e.symbol) or 0)
            except Exception:
                price = None
            snapshot = {
                "ts": datetime.now().isoformat(),
                "price": price,
                "targets": e.targets,
            }
            e.reflections.append({"progress": snapshot})
            e.last_check = snapshot["ts"]
            # 触发反思回调
            if callable(reflection_cb):
                try:
                    feedback = reflection_cb(e, price)
                    if feedback:
                        e.reflections.append({"reflection": feedback})
                except Exception:
                    pass
            changed = True
        if changed:
            self.rewrite(entries)

    def _extract_targets(self, ai_out: Dict[str, Any]) -> Dict[str, Any]:
        # 从 AI 输出中尽力解析目标；如果输出结构化，读取止损止盈等
        targets: Dict[str, Any] = {}
        if not ai_out:
            return targets
        out = ai_out.get("output") or {}
        # 允许两种风格：直接字段或嵌套JSON字符串
        if isinstance(out, dict):
            for k in ("stop_loss", "take_profit", "timeframe", "size", "confidence"):
                if k in out:
                    targets[k] = out.get(k)
        return targets

    # ===== 新增：查询最近反思与长期摘要 =====
    def query_recent_reflections(
        self,
        symbol: str,
        action: str | None = None,
        days: int = 7,
        limit: int = 3,
        only_open: bool = True,
    ) -> list[dict]:
        from datetime import datetime, timedelta
        entries = self.load_all()
        cutoff = datetime.now() - timedelta(days=days)
        out: list[dict] = []
        for e in reversed(entries):
            if only_open and e.status != "open":
                continue
            if e.symbol != symbol:
                continue
            if action and e.action != action:
                continue
            try:
                created = datetime.fromisoformat(e.created_at)
            except Exception:
                created = cutoff
            if created < cutoff:
                continue
            # 取最后一条反思或progress作为摘要来源
            summary = None
            for rec in reversed(e.reflections):
                if rec.get("reflection"):
                    summary = rec["reflection"].get("ai", {}).get("output")
                    break
            if summary is None and e.reflections:
                summary = e.reflections[-1]
            out.append({
                "id": e.id,
                "created_at": e.created_at,
                "reason": e.reason,
                "targets": e.targets,
                "summary": summary,
            })
            if len(out) >= limit:
                break
        return out

    def summarize_long_term(self, symbol: str, days: int = 30) -> str:
        """简要生成长期记忆摘要（启发式拼接，控制体量）。"""
        items = self.query_recent_reflections(symbol=symbol, action=None, days=days, limit=10, only_open=False)
        if not items:
            return ""
        parts = []
        for it in items[:5]:
            parts.append(f"- {it.get('created_at')}: {str(it.get('summary'))[:160]}")
        return "\n".join(parts)


