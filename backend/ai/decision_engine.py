from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd

from core.event_engine.event_manager import Event, EventManager, EventType
from data.cache.market_cache import MarketCache
from ai.api_manager import AIAPIManager
from ai.prompt_manager import PromptManager


class DecisionEngine:
    def __init__(self, market_cache: MarketCache, api_mgr: AIAPIManager, prompt_mgr: PromptManager, event_mgr: EventManager, get_account_info=None, trade_memory=None):
        self.market_cache = market_cache
        self.api_mgr = api_mgr
        self.prompt_mgr = prompt_mgr
        self.event_mgr = event_mgr
        self.get_account_info = get_account_info
        self.trade_memory = trade_memory
        # 去重：避免相同信号重复生成AI决策（基于 symbol+action，60秒内不重复）
        self._decision_cache = {}  # {(symbol, action): last_processed_timestamp}
        import time
        self._cache_timeout = 60.0  # 60秒内不重复处理（增加到60秒以减少频率）

    async def on_strategy_signal(self, event: Event) -> None:
        data = event.data
        symbol = str(data.get("symbol", ""))
        action = str(data.get("action", ""))
        
        # 去重检查：30秒内相同 symbol+action 不重复处理
        # 注意：不使用timestamp作为key的一部分，否则永远不会命中缓存
        import time
        cache_key = (symbol, action)  # 只基于标的和方向去重
        current_time = time.time()
        
        # 清理过期缓存
        expired_keys = [k for k, v in self._decision_cache.items() if current_time - v > self._cache_timeout]
        for k in expired_keys:
            del self._decision_cache[k]
        
        # 检查是否最近已处理过
        if cache_key in self._decision_cache:
            import logging
            logger = logging.getLogger(__name__)
            last_time = self._decision_cache[cache_key]
            elapsed = current_time - last_time
            logger.info(f"[决策去重] 跳过重复信号: {symbol} {action}，距离上次处理仅 {elapsed:.1f}秒（冷却期 {self._cache_timeout}秒）")
            return
        
        # 记录本次处理
        self._decision_cache[cache_key] = current_time
        # 限制缓存大小
        if len(self._decision_cache) > 100:
            oldest_key = min(self._decision_cache.items(), key=lambda x: x[1])[0]
            del self._decision_cache[oldest_key]
        
        context_bars = self.market_cache.get_bars(symbol, limit=200)
        # 序列化原始市场数据（从缓存获取的标准 Bar）
        market_bars = [
            {
                "symbol": b.symbol,
                "start": b.start.isoformat() if hasattr(b.start, "isoformat") else str(b.start),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "period": b.period,
            }
            for b in context_bars
        ]
        # 计算增强特征
        current_price = None
        key_levels: Dict[str, float] = {}
        signal_strength = None
        volatility_ratio = None
        if context_bars:
            rows = [
                {
                    "start": b.start,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": float(b.volume),
                }
                for b in context_bars
            ]
            df = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)
            current_price = float(df["close"].iloc[-1])
            key_levels = {
                "recent_high": float(df["high"].tail(50).max()),
                "recent_low": float(df["low"].tail(50).min()),
            }
            tp = (df["high"] + df["low"] + df["close"]) / 3.0
            cum_vol = df["volume"].cumsum().replace(0, pd.NA)
            vwap_series = (tp * df["volume"]).cumsum() / cum_vol
            vwap_last = float(vwap_series.iloc[-1]) if pd.notna(vwap_series.iloc[-1]) else current_price
            signal_strength = abs(current_price - vwap_last) / max(vwap_last, 1e-8) if vwap_last else None
            ret = df["close"].pct_change().dropna()
            volatility_ratio = float(ret.tail(50).std()) if not ret.empty else 0.0

        # 是否注入反思：仅同标的+同方向且未达成目标
        recent_reflections_str = ""
        long_term_summary = ""
        try:
            if self.trade_memory and symbol and data.get("action"):
                same_dir = data.get("action")
                # 粗略判断未达成：根据 targets 与 current_price 关系
                pending = True
                try:
                    tgt = data.get("targets") or {}
                    if same_dir == "buy" and tgt.get("take_profit"):
                        if current_price and current_price >= float(tgt["take_profit"]):
                            pending = False
                    if same_dir == "sell" and tgt.get("take_profit"):
                        if current_price and current_price <= float(tgt["take_profit"]):
                            pending = False
                except Exception:
                    pending = True
                if pending:
                    recents = self.trade_memory.query_recent_reflections(symbol=symbol, action=same_dir, days=7, limit=3, only_open=True)
                    if recents:
                        bullets = []
                        for r in recents:
                            bullets.append(f"- {r.get('created_at')}: {str(r.get('summary'))[:160]}")
                        recent_reflections_str = "\n".join(bullets)
                    long_term_summary = self.trade_memory.summarize_long_term(symbol=symbol, days=30)
        except Exception:
            pass

        prompt = self.prompt_mgr.render(
            "ai_decision",
            symbol=symbol,
            action=data.get("action"),
            reason=data.get("reason"),
            bars=len(context_bars),
            current_price=current_price,
            key_levels=key_levels,
            signal_strength=signal_strength,
            volatility_ratio=volatility_ratio,
            recent_reflections=recent_reflections_str,
            lt_summary=long_term_summary,
        )
        messages = [
            {"role": "system", "content": "You are a trading assistant."},
            {"role": "user", "content": prompt},
        ]
        # 附加账户信息（若可用）
        account_snapshot = None
        if callable(self.get_account_info):
            try:
                account_snapshot = self.get_account_info()
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[账户信息] 获取结果: {account_snapshot}")
                if not account_snapshot or not account_snapshot.get("ok"):
                    logger.warning(f"[账户信息] 获取失败或返回错误: {account_snapshot}")
                else:
                    cash = account_snapshot.get("cash")
                    power = account_snapshot.get("power")
                    logger.info(f"[账户信息] 现金: {cash}, 购买力: {power}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"[账户信息] 获取异常: {e}", exc_info=True)
                account_snapshot = None
        result = self.api_mgr.generate_insight({"messages": messages, "account": account_snapshot})
        
        # 记录DeepSeek原始响应到日志文件
        if result.get("ok") and result.get("provider") == "deepseek":
            try:
                import os
                import json
                from datetime import datetime
                
                # 确保logs目录存在
                log_dir = "logs"
                os.makedirs(log_dir, exist_ok=True)
                
                # 日志文件路径
                log_file = os.path.join(log_dir, "deepseek_responses.jsonl")
                
                # 提取内容文本
                content = ""
                raw_response = result.get("raw", {})
                if isinstance(raw_response, dict):
                    try:
                        choices = raw_response.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                    except Exception:
                        pass
                
                # 记录日志条目
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": symbol,
                    "action": data.get("action"),
                    "raw_response": raw_response,
                    "content": content,
                }
                
                # 追加到日志文件
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"[DeepSeek日志] 已记录原始响应到 {log_file}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"[DeepSeek日志] 记录失败: {e}", exc_info=True)

        await self.event_mgr.emit_event(
            Event(
                event_type=EventType.SYSTEM_EVENT,
                data={
                    "type": "AI_DECISION",
                    "symbol": symbol,
                    "strategy_action": data.get("action"),
                    "ai": result,
                    "market_bars": market_bars,
                    "original_signal": {
                        "qty": data.get("qty") or data.get("quantity"),
                        "price": data.get("price"),
                        "confidence": data.get("confidence"),
                    },
                    "ai_input": {
                        "symbol": symbol,
                        "action": data.get("action"),
                        "reason": data.get("reason"),
                        "bars": len(context_bars),
                        "current_price": current_price,
                        "key_levels": key_levels,
                        "signal_strength": signal_strength,
                        "volatility_ratio": volatility_ratio,
                        "account": account_snapshot,
                    },
                },
                timestamp=event.timestamp,
                source="decision_engine",
            )
        )


