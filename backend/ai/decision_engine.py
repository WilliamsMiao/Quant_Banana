from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import re
from datetime import datetime

from core.event_engine.event_manager import Event, EventManager, EventType
from data.cache.market_cache import MarketCache
from ai.api_manager import AIAPIManager
from ai.prompt_manager import PromptManager
from core.trading_engine.signal_fusion import (
    SignalFusionEngine, SignalFilter, TradingSignal, 
    SignalSource, SignalDirection
)


class DecisionEngine:
    def __init__(self, market_cache: MarketCache, api_mgr: AIAPIManager, prompt_mgr: PromptManager, event_mgr: EventManager, get_account_info=None, trade_memory=None, fusion_config=None, filter_config=None):
        self.market_cache = market_cache
        self.api_mgr = api_mgr
        self.prompt_mgr = prompt_mgr
        self.event_mgr = event_mgr
        self.get_account_info = get_account_info
        self.trade_memory = trade_memory
        
        # 初始化信号融合引擎和过滤器
        self.fusion_engine = SignalFusionEngine(config=fusion_config or {})
        self.signal_filter = SignalFilter(config=filter_config or {})
        
        # 去重：避免相同信号重复生成AI决策（基于 symbol+action，60秒内不重复）
        self._decision_cache = {}  # {(symbol, action): last_processed_timestamp}
        import time
        self._cache_timeout = 60.0  # 60秒内不重复处理（增加到60秒以减少频率）

    def _parse_ai_direction(self, ai_output: Dict[str, Any]) -> SignalDirection:
        """从AI输出中解析操作方向"""
        # 从normalized输出或原始文本中提取
        summary_text = ""
        if isinstance(ai_output, dict):
            summary_text = str(ai_output.get("summary") or ai_output.get("text") or "")
        else:
            summary_text = str(ai_output)
        
        # 提取操作方向（支持多种格式）
        direction_patterns = [
            r'\*\*操作方向\*\*[：:]\s*(buy|sell|hold|买入|卖出|持有)',  # Markdown
            r'操作方向[：:]\s*(buy|sell|hold|买入|卖出|持有)',  # 普通格式
            r'方向[：:]\s*(buy|sell|hold|买入|卖出|持有)',
        ]
        
        for pattern in direction_patterns:
            match = re.search(pattern, summary_text, re.IGNORECASE)
            if match:
                direction_str = match.group(1).lower()
                return SignalDirection.from_str(direction_str)
        
        # 如果没找到，默认HOLD
        import logging
        logging.getLogger(__name__).warning(f"无法解析AI方向，使用默认HOLD。文本片段: {summary_text[:200]}")
        return SignalDirection.HOLD

    def _create_strategy_signal(self, data: Dict, symbol: str, current_price: float, account_snapshot: Optional[Dict] = None) -> TradingSignal:
        """将策略信号转换为TradingSignal"""
        strategy_action = str(data.get("action", "")).upper()
        strategy_direction = SignalDirection.from_str(strategy_action)
        
        # 提取数量和价格
        qty = float(data.get("qty") or data.get("quantity") or 0)
        price = float(data.get("price") or current_price)
        
        # 计算仓位大小（如果没有，默认最小单位）
        position_size = int(qty) if qty > 0 else 100
        
        # 从账户信息更新过滤器资金
        if account_snapshot and account_snapshot.get("ok"):
            capital = account_snapshot.get("power") or account_snapshot.get("cash") or 0
            if capital:
                self.signal_filter.update_capital(float(capital))
        
        # 置信度转换（0-1 -> 0-100）
        confidence = float(data.get("confidence", 0.5)) * 100
        
        # 止损和止盈（如果没有，使用默认值）
        stop_loss = price * 0.985 if strategy_direction == SignalDirection.BUY else price * 1.015
        take_profit = price * 1.03 if strategy_direction == SignalDirection.BUY else price * 0.97
        
        return TradingSignal(
            source=SignalSource.STRATEGY_ENGINE,
            direction=strategy_direction,
            symbol=symbol,
            timestamp=datetime.now(),
            confidence=confidence,
            price=price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=str(data.get("reason", "")),
            metadata={'strategy_type': 'quantitative'}
        )

    def _create_ai_signal(self, ai_output: Dict[str, Any], symbol: str, current_price: float, account_snapshot: Optional[Dict] = None) -> TradingSignal:
        """将AI输出转换为TradingSignal"""
        # 解析方向
        ai_direction = self._parse_ai_direction(ai_output)
        
        # 提取字段（使用formatters中的逻辑）
        from utils.formatters import _extract_fields_from_text
        summary_text = str(ai_output.get("summary", "")) if isinstance(ai_output, dict) else str(ai_output)
        fields = _extract_fields_from_text(summary_text)
        
        # 置信度（0-100）
        confidence = float(fields.get("confidence") or 0.5) * 100
        if confidence > 100:
            confidence = 100
        
        # 止损和止盈
        stop_loss = fields.get("stop_loss") or (current_price * 0.985 if ai_direction == SignalDirection.BUY else current_price * 1.015)
        take_profit = fields.get("take_profit") or (current_price * 1.03 if ai_direction == SignalDirection.BUY else current_price * 0.97)
        
        # 仓位大小（从仓位权重和账户资金计算）
        position_weight = float(fields.get("position") or 0)
        if position_weight > 1:
            position_weight = position_weight / 100.0  # 如果是百分比形式
        
        position_size = 0
        if account_snapshot and account_snapshot.get("ok"):
            capital = account_snapshot.get("power") or account_snapshot.get("cash") or 0
            if capital and position_weight > 0:
                position_value = float(capital) * position_weight
                position_size = int(position_value / current_price) if current_price > 0 else 0
                # 港股整手调整
                if symbol.startswith("HK.") and position_size > 0:
                    if position_size % 100 != 0:
                        position_size = ((position_size // 100) + 1) * 100
                    if position_size < 100:
                        position_size = 100
        
        return TradingSignal(
            source=SignalSource.AI_DECISION,
            direction=ai_direction,
            symbol=symbol,
            timestamp=datetime.now(),
            confidence=confidence,
            price=current_price,
            position_size=position_size,
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            reason=summary_text[:500] if summary_text else "AI决策",
            metadata={'ai_model': 'deepseek'}
        )

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

        # 注意：不再将action传给AI，让AI自主判断方向
        prompt = self.prompt_mgr.render(
            "ai_decision",
            symbol=symbol,
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

        # 解析AI输出并创建信号
        ai_output = result.get("output", {}) if isinstance(result, dict) else result
        strategy_signal = None
        ai_signal = None
        fused_signal = None
        direction_match = False
        fusion_type = None
        
        try:
            # 创建策略信号
            strategy_signal = self._create_strategy_signal(data, symbol, current_price or 0, account_snapshot)
            
            # 创建AI信号
            ai_signal = self._create_ai_signal(ai_output, symbol, current_price or 0, account_snapshot)
            
            # 进行信号融合
            fused_signal = self.fusion_engine.fuse_signals(strategy_signal, ai_signal)
            
            # 检查方向一致性
            direction_match = strategy_signal.direction == ai_signal.direction
            fusion_type = fused_signal.metadata.get("fusion_type", "unknown")
            
            # 应用信号质量过滤
            should_accept, filter_reason = self.signal_filter.should_accept_signal(fused_signal)
            if not should_accept:
                import logging
                logging.getLogger(__name__).info(f"[信号过滤] 融合信号被拒绝: {filter_reason}")
                # 如果被过滤，标记为不应执行
                fused_signal = TradingSignal(
                    source=fused_signal.source,
                    direction=SignalDirection.HOLD,
                    symbol=fused_signal.symbol,
                    timestamp=fused_signal.timestamp,
                    confidence=0,
                    price=fused_signal.price,
                    position_size=0,
                    stop_loss=0,
                    take_profit=0,
                    reason=f"信号被过滤: {filter_reason}",
                    metadata={'filter_reason': filter_reason, **fused_signal.metadata}
                )
            
            # 记录冲突情况（如果方向不一致）
            if not direction_match:
                self._log_signal_conflict(strategy_signal, ai_signal, fused_signal)
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[信号融合] 处理失败: {e}", exc_info=True)
            # 降级处理：创建默认信号
            if not strategy_signal:
                strategy_signal = self._create_strategy_signal(data, symbol, current_price or 0, account_snapshot)
            if not ai_signal:
                ai_signal = TradingSignal(
                    source=SignalSource.AI_DECISION,
                    direction=SignalDirection.HOLD,
                    symbol=symbol,
                    timestamp=datetime.now(),
                    confidence=0,
                    price=current_price or 0,
                    position_size=0,
                    stop_loss=0,
                    take_profit=0,
                    reason=f"AI解析失败: {str(e)}",
                    metadata={'error': str(e)}
                )
            if not fused_signal:
                fused_signal = ai_signal  # 降级为AI信号

        # 将信号转换为可序列化的字典（用于事件数据）
        def signal_to_dict(sig: TradingSignal) -> Dict:
            if sig is None:
                return None
            return {
                'source': sig.source.value,
                'direction': sig.direction.value,
                'symbol': sig.symbol,
                'timestamp': sig.timestamp.isoformat() if hasattr(sig.timestamp, 'isoformat') else str(sig.timestamp),
                'confidence': sig.confidence,
                'price': sig.price,
                'position_size': sig.position_size,
                'stop_loss': sig.stop_loss,
                'take_profit': sig.take_profit,
                'reason': sig.reason,
                'metadata': sig.metadata,
            }

        await self.event_mgr.emit_event(
            Event(
                event_type=EventType.SYSTEM_EVENT,
                data={
                    "type": "AI_DECISION",
                    "symbol": symbol,
                    "strategy_action": data.get("action"),
                    "ai": result,
                    "market_bars": market_bars,
                    # 新增：信号融合相关字段
                    "strategy_signal": signal_to_dict(strategy_signal),
                    "ai_signal": signal_to_dict(ai_signal),
                    "fused_signal": signal_to_dict(fused_signal),
                    "direction_match": direction_match,
                    "fusion_type": fusion_type,
                    # 保留原有字段（向后兼容）
                    "original_signal": {
                        "qty": data.get("qty") or data.get("quantity"),
                        "price": data.get("price"),
                        "confidence": data.get("confidence"),
                    },
                    "ai_input": {
                        "symbol": symbol,
                        "reason": data.get("reason"),  # 不再包含action
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
    
    def _log_signal_conflict(self, strategy_signal: TradingSignal, ai_signal: TradingSignal, fused_signal: TradingSignal):
        """记录信号冲突到日志文件"""
        try:
            import os
            import json
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "signal_conflicts.jsonl")
            
            conflict_entry = {
                "timestamp": datetime.now().isoformat(),
                "symbol": strategy_signal.symbol,
                "strategy_direction": strategy_signal.direction.value,
                "strategy_confidence": strategy_signal.confidence,
                "ai_direction": ai_signal.direction.value,
                "ai_confidence": ai_signal.confidence,
                "direction_match": False,
                "fusion_type": fused_signal.metadata.get("fusion_type"),
                "fused_direction": fused_signal.direction.value,
                "fused_confidence": fused_signal.confidence,
                "fused_reason": fused_signal.reason,
            }
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(conflict_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"记录信号冲突失败: {e}")


