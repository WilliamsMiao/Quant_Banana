from __future__ import annotations

import asyncio
import logging
from typing import List

import os
import yaml
import os

from core.event_engine.event_manager import EventManager, EventType, Event
from core.trading_engine.order_manager import OrderManager
from core.trading_engine.strategy_runner import StrategyRunner
from data.market_data.futu_provider import FutuMarketDataProvider
from data.cache.market_cache import MarketCache
from strategies.strategy_library.technical.intraday_vwap_reversion import (
    IntradayVWAPReversionStrategy,
)
from strategies.strategy_library.technical.optimized_hk_intraday import (
    OptimizedHKIntradayStrategy,
)
from ai.api_manager import AIAPIManager
from ai.prompt_manager import PromptManager
from ai.ai_gateway import AIGateway
from ai.decision_engine import DecisionEngine
from utils.dingtalk_bot import DingTalkBot
from utils.formatters import format_ai_decision
from ai.trade_memory import TradeMemory


logging.basicConfig(level=logging.INFO)


def load_config() -> dict:
    """加载配置文件，从base.yaml读取基础配置，从secrets.yaml读取敏感信息并合并"""
    # 加载基础配置
    with open("config/settings/base.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    
    # 从secrets.yaml加载所有敏感信息
    secrets_path = "config/secrets/secrets.yaml"
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as sf:
            secrets = yaml.safe_load(sf) or {}
            
            # 合并Futu ws_key
            if "futu" in secrets and "ws_key" in secrets["futu"]:
                if "api" not in cfg:
                    cfg["api"] = {}
                if "futu" not in cfg["api"]:
                    cfg["api"]["futu"] = {}
                cfg["api"]["futu"]["ws_key"] = secrets["futu"]["ws_key"]
            
            # 合并iTick token
            if "itick" in secrets:
                if "api" not in cfg:
                    cfg["api"] = {}
                if "itick" not in cfg["api"]:
                    cfg["api"]["itick"] = {}
                if "token" in secrets["itick"]:
                    cfg["api"]["itick"]["token"] = secrets["itick"]["token"]
            
            # 合并新浪云配置
            if "sina" in secrets:
                if "api" not in cfg:
                    cfg["api"] = {}
                if "sina" not in cfg["api"]:
                    cfg["api"]["sina"] = {}
                if "access_key" in secrets["sina"]:
                    cfg["api"]["sina"]["access_key"] = secrets["sina"]["access_key"]
                if "secret_key" in secrets["sina"]:
                    cfg["api"]["sina"]["secret_key"] = secrets["sina"]["secret_key"]
            
            # 创建secrets配置节点（用于provider_factory）
            cfg["secrets"] = {
                "futu": secrets.get("futu", {}),
                "itick": secrets.get("itick", {}),
                "sina": secrets.get("sina", {}),
            }
            
            # 合并钉钉配置
            if "dingding" in secrets:
                cfg["dingding"] = secrets["dingding"]
            if "dingding_tuning" in secrets:
                cfg["dingding_tuning"] = secrets["dingding_tuning"]
            
            # 合并数据库密码（如果secrets中有）
            if "database" in secrets and "password" in secrets["database"]:
                if "database" not in cfg:
                    cfg["database"] = {}
                db_password = secrets["database"]["password"]
                db_url = cfg["database"].get("url", "postgresql://user:password@localhost:5432/quant_trading")
                # 替换URL中的密码
                import re
                cfg["database"]["url"] = re.sub(
                    r'(://[^:]+:)([^@]+)(@)',
                    rf'\1{db_password}\3',
                    db_url
                )
    
    return cfg


async def main():
    cfg = load_config()
    md_cfg = cfg.get("market_data", {}).get("subscription", {})

    # 使用ProviderFactory创建多数据源管理器
    from data.market_data.provider_factory import ProviderFactory, MultiProviderManager
    
    primary_provider, fallback_providers = ProviderFactory.create_providers_from_config(cfg)
    
    if not primary_provider:
        raise RuntimeError("无法创建主数据源，请检查配置")
    
    # 创建多数据源管理器
    provider_manager = MultiProviderManager(primary_provider, fallback_providers)
    
    # 获取当前使用的数据源（默认是主数据源）
    provider = provider_manager.get_provider()
    if not provider:
        raise RuntimeError("没有可用的数据源")
    market_cache = MarketCache(maxlen=2000)
    event_mgr = EventManager()
    order_mgr = OrderManager()

    symbols: List[str] = list(md_cfg.get("symbols", []))
    period: str = str(md_cfg.get("period", "1m"))

    runner = StrategyRunner(
        provider=provider,
        event_mgr=event_mgr,
        order_mgr=order_mgr,
        market_cache=market_cache,
        period=period,
        pull_interval_sec=2.0,
        lookback=200,
    )
    
    # 保存provider_manager引用以便故障转移
    runner.provider_manager = provider_manager

    # AI 组件注册
    # 载入 secrets（DeepSeek api_key）
    secrets = {}
    if os.path.exists("config/secrets/api-keys.yaml"):
        with open("config/secrets/api-keys.yaml", "r", encoding="utf-8") as sf:
            secrets = yaml.safe_load(sf) or {}

    # DeepSeek 客户端
    deepseek_key = ((secrets or {}).get("deepseek") or {}).get("api_key")
    from api_clients.deepseek_client.client import DeepSeekClient
    ds_client = DeepSeekClient(api_key=deepseek_key, base_url=str(cfg.get("api", {}).get("deepseek", {}).get("base_url", "https://api.deepseek.com"))) if deepseek_key else None

    ai_mgr = AIAPIManager(deepseek=ds_client)
    prompt_mgr = PromptManager()
    # 注册 AI 决策模板
    prompt_mgr.register(
        "ai_decision",
        (
            "# 量化交易决策指令\n"
            "你是一个严格执行纪律的量化交易系统。基于提供的市场数据和技术指标，自主判断交易方向并输出明确的交易决策。\n\n"
            "# 重要提示\n"
            "你**必须自主判断**交易方向（买入/卖出/持有），不要被任何提示影响。只基于市场数据和技术指标做出判断。\n\n"
            "# 输入数据（REQUIRED_FIELDS）\n"
            "symbol={symbol}\n"
            "策略信号原因: {reason}\n"
            "bars={bars}\n"
            "current_price={current_price}\n"
            "key_levels={key_levels}\n"
            "signal_strength={signal_strength}\n"
            "volatility_ratio={volatility_ratio}\n\n"
            "# 历史反思（最近）\n"
            "{recent_reflections}\n\n"
            "# 长期记忆摘要\n"
            "{lt_summary}\n\n"
            "# 决策输出格式（严格遵循）\n"
            "## 最终决策\n"
            "[执行交易｜放弃交易]\n\n"
            "## 决策详情\n"
            "**操作方向**: [必须明确输出：buy/买入、sell/卖出、hold/持有 三者之一]\n"
            "**信心度**: [0-100]%\n"
            "**仓位权重**: [0-100%]\n"
            "**止损价格**: [具体数值，如无则填0]\n"
            "**止盈目标**: [具体数值，如无则填0]\n\n"
            "## 决策依据\n"
            "1. 关键因素: 简述你判断方向的关键因素\n"
            "2. 风险收益比: 量化描述（如选择持有，说明原因）\n"
            "3. 时间框架匹配: 简述\n\n"
            "注意：操作方向必须是 buy/sell/hold 之一，不要输出其他值。"
        ),
    )
    # 注册 AI 反思模板
    prompt_mgr.register(
        "ai_reflect",
        (
            "# 交易反思\n"
            "标的: {symbol}\n"
            "动作: {action}\n"
            "原因: {reason}\n"
            "当前价: {price}\n"
            "目标: {targets}\n"
            "上次AI摘要: {last_summary}\n\n"
            "请评估: (1) 目标达成进度 (2) 信号有效性变化 (3) 是否需要调整止损/止盈/仓位 (4) 下一步动作。"
        ),
    )
    ai_gateway = AIGateway(ai_mgr, prompt_mgr, event_mgr)
    # 账户信息获取器（按需查询）
    def fetch_account_info():
        from api_clients.futu_client.client import FutuClient
        # 从配置中获取futu配置
        futu_cfg_local = cfg.get("api", {}).get("futu", {})
        futu_secrets = cfg.get("secrets", {}).get("futu", {})
        ws_key = futu_secrets.get("ws_key", "")
        c = FutuClient(
            host=str(futu_cfg_local.get("host", "127.0.0.1")),
            api_port=int(futu_cfg_local.get("api_port", 11111)),
            ws_port=int(futu_cfg_local.get("ws_port", 33333)),
            ws_key=str(ws_key)
        )
        try:
            c.connect()
            return c.get_account_info()
        finally:
            c.close()

    # 交易记忆
    journal = TradeMemory(storage_path="data/trade_journal.jsonl")
    
    # 信号融合配置
    fusion_cfg = (cfg.get("signal_fusion", {}) or {})
    fusion_config = {
        "source_weights": fusion_cfg.get("source_weights", {"strategy": 0.45, "ai": 0.55}),
        "performance_file": fusion_cfg.get("performance_file", "data/signal_performance.json"),
    }
    filter_config = {
        "min_confidence": float(fusion_cfg.get("min_confidence", 60)),
        "min_risk_reward": float(fusion_cfg.get("min_risk_reward", 1.3)),
        "max_position_ratio": float(fusion_cfg.get("max_position_ratio", 0.3)),
        "cooldown_period_minutes": int(fusion_cfg.get("cooldown_period_minutes", 10)),
        "initial_capital": float(cfg.get("strategy", {}).get("optimized_hk_intraday", {}).get("initial_capital", 10000)),
    }
    
    decision_engine = DecisionEngine(
        market_cache, ai_mgr, prompt_mgr, event_mgr, 
        get_account_info=fetch_account_info, 
        trade_memory=journal,
        fusion_config=fusion_config,
        filter_config=filter_config
    )
    event_mgr.register_handler(EventType.MARKET_DATA, ai_gateway.on_event)
    event_mgr.register_handler(EventType.STRATEGY_SIGNAL, ai_gateway.on_event)
    event_mgr.register_handler(EventType.STRATEGY_SIGNAL, decision_engine.on_strategy_signal)
    # 占位：打印 AI 决策
    ding_cfg = cfg.get("dingding", {})
    ding_tune_cfg = cfg.get("dingding_tuning", {})
    bots = []
    if ding_cfg.get("webhook"):
        bots.append(DingTalkBot(ding_cfg.get("webhook", ""), ding_cfg.get("secret", "")))
    if ding_tune_cfg.get("webhook"):
        bots.append(DingTalkBot(ding_tune_cfg.get("webhook", ""), ding_tune_cfg.get("secret", "")))

    # 订单冷却期：同一标的、同一方向，在冷却期内不重复下单
    # {(symbol, side): last_order_timestamp}
    order_cooldown_cache = {}
    ORDER_COOLDOWN_SEC = 300  # 5分钟冷却期
    
    # 辅助函数：将字典转换为TradingSignal（用于性能跟踪）
    def _dict_to_trading_signal(signal_dict: dict, symbol: str):
        """将信号字典转换为TradingSignal对象"""
        from core.trading_engine.signal_fusion import TradingSignal, SignalSource, SignalDirection
        from datetime import datetime as dt
        
        if not signal_dict:
            return None
            
        source_str = signal_dict.get("source", "ai_decision")
        try:
            source = SignalSource(source_str)
        except ValueError:
            source = SignalSource.AI_DECISION
        
        direction_str = signal_dict.get("direction", "")
        try:
            direction = SignalDirection(direction_str)
        except ValueError:
            direction = SignalDirection.HOLD
        
        timestamp_str = signal_dict.get("timestamp", "")
        if isinstance(timestamp_str, str) and timestamp_str:
            try:
                timestamp = dt.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except:
                timestamp = dt.now()
        else:
            timestamp = dt.now()
        
        return TradingSignal(
            source=source,
            direction=direction,
            symbol=symbol,
            timestamp=timestamp,
            confidence=float(signal_dict.get("confidence", 0)),
            price=float(signal_dict.get("price", 0)),
            position_size=int(signal_dict.get("position_size", 0)),
            stop_loss=float(signal_dict.get("stop_loss", 0)),
            take_profit=float(signal_dict.get("take_profit", 0)),
            reason=str(signal_dict.get("reason", "")),
            metadata=signal_dict.get("metadata", {})
        )
    
    async def print_ai_decision(evt):
        if evt.event_type == EventType.SYSTEM_EVENT and evt.data.get("type") == "AI_DECISION":
            # 记录交易意图
            try:
                journal.record_ai_decision({"data": evt.data})
            except Exception:
                pass
            print("AI_DECISION:", evt.data.get("symbol"), evt.data.get("ai", {}))
            
            # 使用融合后的信号进行决策
            fused_signal = evt.data.get("fused_signal")
            direction_match = evt.data.get("direction_match", False)
            fusion_type = evt.data.get("fusion_type", "unknown")
            
            # 判断是否执行：融合信号方向不为HOLD，且置信度足够
            should_execute = False
            execution_direction = None
            execution_qty = 0
            execution_price = None
            
            if fused_signal:
                direction = fused_signal.get("direction", "").upper()
                confidence = float(fused_signal.get("confidence", 0))
                min_confidence = float(cfg.get("signal_fusion", {}).get("min_confidence", 60))
                
                # 只有当方向不为HOLD且置信度足够时才执行
                if direction != "HOLD" and confidence >= min_confidence:
                    should_execute = True
                    execution_direction = direction
                    execution_qty = int(fused_signal.get("position_size", 0))
                    execution_price = float(fused_signal.get("price", 0)) if fused_signal.get("price") else None
            
            # 只在执行交易时推送（且仅当下单成功或失败有明确结果时）
            # 注意：推送和下单是同步的，但只有下单尝试后才推送
            order_result = None
            if should_execute and execution_direction:
                import time
                symbol = evt.data.get("symbol")
                side = execution_direction  # 使用融合信号的方向
                
                # 检查冷却期
                cooldown_key = (symbol, side)
                current_time = time.time()
                
                if cooldown_key in order_cooldown_cache:
                    last_order_time = order_cooldown_cache[cooldown_key]
                    elapsed = current_time - last_order_time
                    if elapsed < ORDER_COOLDOWN_SEC:
                        remaining = ORDER_COOLDOWN_SEC - elapsed
                        print(f"[下单冷却] {symbol} {side}: 距离上次下单仅 {elapsed:.1f}秒，需等待 {remaining:.1f}秒（冷却期 {ORDER_COOLDOWN_SEC}秒）")
                        order_result = {"ok": False, "error": f"冷却期中（还需等待 {int(remaining)}秒）", "cooldown": True}
                    else:
                        # 冷却期已过，可以下单
                        pass
                else:
                    # 首次下单，无冷却期限制
                    pass
                
                # 如果处于冷却期，跳过下单
                if order_result and order_result.get("cooldown", False):
                    pass  # 已在冷却期检查中设置 order_result
                else:
                    # 使用融合信号的数量和价格
                    qty = execution_qty
                    price = execution_price
                    
                    # 如果没有，尝试从原始信号获取（降级处理）
                    if not qty or qty <= 0:
                        try:
                            sig_data = evt.data.get("original_signal", {})
                            qty = int(sig_data.get("qty") or sig_data.get("quantity") or 0)
                            price = float(sig_data.get("price") or 0) if sig_data.get("price") else price
                        except Exception:
                            pass
                    
                    # 若仍然没有，使用默认最小单位
                    if not qty or qty <= 0:
                        qty = 100  # 默认100股
                    
                    # 港股整手数量调整：向上取整到100的倍数（100股为1手）
                    # 例如：541股 → 600股，99股 → 100股，150股 → 200股
                    if qty > 0:
                        # 判断是否为港股（HK.开头）
                        is_hk_stock = symbol.startswith("HK.")
                        if is_hk_stock:
                            # 向上取整到100的倍数
                            if qty % 100 != 0:
                                original_qty = qty
                                qty = ((qty // 100) + 1) * 100
                                print(f"[整手调整] {symbol}: {original_qty}股 → {qty}股（港股要求100股为1手）")
                            # 确保最小为100股
                            if qty < 100:
                                qty = 100
                                print(f"[整手调整] {symbol}: 数量不足100股，调整为最小100股")
                    
                    if qty > 0:
                        from api_clients.futu_client.client import FutuClient
                        futu_cfg_local = cfg.get("api", {}).get("futu", {})
                        futu_secrets = cfg.get("secrets", {}).get("futu", {})
                        ws_key = futu_secrets.get("ws_key", "")
                        trade_client = FutuClient(
                            host=str(futu_cfg_local.get("host", "127.0.0.1")),
                            api_port=int(futu_cfg_local.get("api_port", 11111)),
                            ws_port=int(futu_cfg_local.get("ws_port", 33333)),
                            ws_key=str(ws_key),
                        )
                        try:
                            trade_client.connect()
                            result = trade_client.place_order(
                                symbol=symbol,
                                side=side,
                                qty=qty,
                                price=price,
                                order_type="MARKET" if price is None else "LIMIT",
                                env="SIMULATE",
                            )
                            order_result = result
                            if result.get("ok"):
                                print(f"[下单成功] {symbol} {side} {qty}股, order_id={result.get('order_id')}")
                                
                                # 记录交易结果用于性能跟踪
                                try:
                                    # 从事件数据中获取融合信号和原始信号
                                    fused_signal_dict = evt.data.get("fused_signal")
                                    strategy_signal_dict = evt.data.get("strategy_signal")
                                    ai_signal_dict = evt.data.get("ai_signal")
                                    fusion_type = evt.data.get("fusion_type", "unknown")
                                    
                                    if fused_signal_dict:
                                        from core.trading_engine.signal_fusion import TradingSignal, SignalSource, SignalDirection
                                        from datetime import datetime as dt
                                        
                                        # 根据融合类型决定如何跟踪
                                        if fusion_type == "agreed":
                                            # 方向一致：策略和AI都成功
                                            if strategy_signal_dict:
                                                strat_signal = _dict_to_trading_signal(strategy_signal_dict, symbol)
                                                if strat_signal:
                                                    decision_engine.fusion_engine.record_trade_outcome(strat_signal, True, 0.0)
                                            if ai_signal_dict:
                                                ai_signal = _dict_to_trading_signal(ai_signal_dict, symbol)
                                                if ai_signal:
                                                    decision_engine.fusion_engine.record_trade_outcome(ai_signal, True, 0.0)
                                        elif fusion_type == "conflict_resolved":
                                            # 冲突解决：胜出方成功，败方失败
                                            winning_source = fused_signal_dict.get("metadata", {}).get("winning_source", "")
                                            if winning_source == "strategy_engine":
                                                if strategy_signal_dict:
                                                    strat_signal = _dict_to_trading_signal(strategy_signal_dict, symbol)
                                                    if strat_signal:
                                                        decision_engine.fusion_engine.record_trade_outcome(strat_signal, True, 0.0)
                                                if ai_signal_dict:
                                                    ai_signal = _dict_to_trading_signal(ai_signal_dict, symbol)
                                                    if ai_signal:
                                                        decision_engine.fusion_engine.record_trade_outcome(ai_signal, False, 0.0)
                                            elif winning_source == "ai_decision":
                                                if ai_signal_dict:
                                                    ai_signal = _dict_to_trading_signal(ai_signal_dict, symbol)
                                                    if ai_signal:
                                                        decision_engine.fusion_engine.record_trade_outcome(ai_signal, True, 0.0)
                                                if strategy_signal_dict:
                                                    strat_signal = _dict_to_trading_signal(strategy_signal_dict, symbol)
                                                    if strat_signal:
                                                        decision_engine.fusion_engine.record_trade_outcome(strat_signal, False, 0.0)
                                        
                                        import logging
                                        logging.getLogger(__name__).info(f"[性能跟踪] 记录交易成功: {symbol} {side}, 融合类型: {fusion_type}, 订单ID: {result.get('order_id')}")
                                except Exception as e:
                                    import logging
                                    logging.getLogger(__name__).warning(f"[性能跟踪] 记录失败: {e}", exc_info=True)
                            else:
                                print(f"[下单失败] {symbol} {side} {qty}股: {result.get('error')}")
                                
                                # 记录交易失败（用于性能跟踪）
                                try:
                                    fusion_type = evt.data.get("fusion_type", "unknown")
                                    strategy_signal_dict = evt.data.get("strategy_signal")
                                    ai_signal_dict = evt.data.get("ai_signal")
                                    
                                    # 交易失败时，记录策略和AI都失败
                                    if fusion_type in ("agreed", "conflict_resolved"):
                                        # 方向一致但执行失败：两个信号源都失败
                                        # 冲突解决但执行失败：胜出方和败方都失败（因为最终执行失败）
                                        if strategy_signal_dict:
                                            strat_signal = _dict_to_trading_signal(strategy_signal_dict, symbol)
                                            if strat_signal:
                                                decision_engine.fusion_engine.record_trade_outcome(strat_signal, False, 0.0)
                                        if ai_signal_dict:
                                            ai_signal = _dict_to_trading_signal(ai_signal_dict, symbol)
                                            if ai_signal:
                                                decision_engine.fusion_engine.record_trade_outcome(ai_signal, False, 0.0)
                                except Exception as e:
                                    import logging
                                    logging.getLogger(__name__).warning(f"[性能跟踪] 记录失败结果失败: {e}")
                        except Exception as e:
                            print(f"[下单异常] {symbol}: {e}")
                            order_result = {"ok": False, "error": str(e)}
                        finally:
                            trade_client.close()
                    else:
                        print(f"[跳过下单] {symbol} {side}: 数量无效({qty})")
                        order_result = {"ok": False, "error": "数量无效"}
                
                # 如果下单成功或失败（非冷却期），更新冷却期缓存
                if order_result and not order_result.get("cooldown", False):
                    cooldown_key = (symbol, side)
                    order_cooldown_cache[cooldown_key] = current_time
                    # 清理过期缓存（保留最近100个）
                    if len(order_cooldown_cache) > 100:
                        expired_keys = [k for k, v in order_cooldown_cache.items() 
                                       if current_time - v > ORDER_COOLDOWN_SEC * 2]
                        for k in expired_keys:
                            del order_cooldown_cache[k]
            
            # 只在执行交易时推送（推送下单结果，但不包括冷却期）
            # 冷却期时不推送，避免刷屏
            if should_execute and bots and order_result is not None and not order_result.get("cooldown", False):
                # 调试：打印账户信息
                import logging
                logger = logging.getLogger(__name__)
                ai_input = evt.data.get("ai_input", {})
                account_debug = ai_input.get("account")
                logger.info(f"[推送前] ai_input: {ai_input}")
                logger.info(f"[推送前] account: {account_debug}")
                logger.info(f"[推送前] evt.data.keys(): {evt.data.keys()}")
                
                # 不再包含原始市场数据
                pretty = format_ai_decision(evt.data)
                # 添加下单结果到推送内容
                order_status = ""
                if order_result:
                    if order_result.get("ok"):
                        order_status = f"\n\n**下单结果**: ✅ 成功\n- 订单ID: {order_result.get('order_id', 'N/A')}"
                    else:
                        order_status = f"\n\n**下单结果**: ❌ 失败\n- 错误: {order_result.get('error', '未知错误')}"
                
                for b in bots:
                    b.send_markdown(
                        title="AI 决策",
                        text_md=(
                            f"{pretty}\n"
                            f"{order_status}\n"
                        ),
                    )
            else:
                symbol = evt.data.get('symbol')
                fused_signal = evt.data.get("fused_signal")
                reason = "未知原因"
                
                if not fused_signal:
                    reason = "未生成融合信号"
                elif fused_signal.get("direction", "").upper() == "HOLD":
                    reason = fused_signal.get("reason", "信号被过滤")
                elif not should_execute:
                    reason = f"条件不满足（方向={fused_signal.get('direction')}, 置信度={fused_signal.get('confidence', 0):.1f}%）"
                
                import logging
                logger_local = logging.getLogger(__name__)
                logger_local.info(f"[AI决策] {symbol}: 放弃交易 - {reason}")
                # 放弃交易时不推送（避免刷屏）
                # 但可以添加日志或统计信息
    event_mgr.register_handler(EventType.SYSTEM_EVENT, print_ai_decision)

    # 策略
    strat_cfg = (cfg.get("strategy", {}) or {}).get("optimized_hk_intraday", {})
    if strat_cfg.get("enabled", False):
        strategy = OptimizedHKIntradayStrategy(config=strat_cfg)
    else:
        strategy = IntradayVWAPReversionStrategy()

    # 启动事件循环
    loop = asyncio.get_event_loop()
    loop.create_task(event_mgr.start())
    # 周期本金刷新（每5分钟）
    async def refresh_capital_task():
        while True:
            try:
                snap = fetch_account_info()
                capital = None
                if isinstance(snap, dict):
                    # 优先购买力，其次现金
                    capital = snap.get("power") or snap.get("cash")
                if capital:
                    try:
                        # 仅当策略支持 update_capital 才调用
                        if hasattr(strategy, "update_capital"):
                            strategy.update_capital(float(capital))
                    except Exception:
                        pass
            except Exception:
                pass
            await asyncio.sleep(300)

    loop.create_task(refresh_capital_task())
    
    # 定期更新信号源权重（每30分钟）
    async def update_fusion_weights_task():
        while True:
            try:
                decision_engine.fusion_engine.update_source_weights()
                import logging
                logging.getLogger(__name__).info("[权重更新] 已更新信号源权重")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"[权重更新] 失败: {e}", exc_info=True)
            await asyncio.sleep(1800)  # 30分钟
    
    loop.create_task(update_fusion_weights_task())
    
    # 周期反思任务（每5分钟刷新一次）
    async def periodic_review():
        from datetime import datetime, timedelta
        ref_cfg = (cfg.get("ai", {}) or {}).get("reflection", {})
        enabled = bool(ref_cfg.get("enabled", False))
        interval_sec = int(ref_cfg.get("interval_sec", 3600))
        price_th = float(ref_cfg.get("price_change_threshold", 0.01))
        max_per_hour = int(ref_cfg.get("max_events_per_hour", 2))
        push_enable = bool(ref_cfg.get("push", True))

        # 全局速率限制状态
        window_start = datetime.now()
        sent_count = 0

        while True:
            try:
                if not enabled:
                    await asyncio.sleep(300)
                    continue

                # 每小时窗口重置
                now = datetime.now()
                if now - window_start >= timedelta(hours=1):
                    window_start = now
                    sent_count = 0

                def get_last_price(sym: str):
                    bars = market_cache.get_bars(sym, limit=2)
                    return bars[-1].close if bars else None

                def reflect_cb(entry, price):
                    nonlocal sent_count
                    # 条目级冷却：基于 last_check
                    if entry.last_check:
                        try:
                            last_ts = datetime.fromisoformat(entry.last_check)
                            if now - last_ts < timedelta(seconds=interval_sec):
                                return None
                        except Exception:
                            pass
                    # 价格变动阈值
                    try:
                        prev_price = None
                        if entry.reflections:
                            # 找到最近一次 progress 记录的价格
                            for rec in reversed(entry.reflections):
                                if isinstance(rec, dict) and rec.get("progress"):
                                    prev_price = rec["progress"].get("price")
                                    break
                        if prev_price and price and prev_price > 0:
                            if abs(price - prev_price) / prev_price < price_th:
                                return None
                    except Exception:
                        pass
                    # 全局速率限制
                    if sent_count >= max_per_hour:
                        return None

                    messages = [
                        {"role": "system", "content": "You are a trading assistant."},
                        {"role": "user", "content": prompt_mgr.render(
                            "ai_reflect",
                            symbol=entry.symbol,
                            action=entry.action,
                            reason=entry.reason,
                            price=price,
                            targets=entry.targets,
                            last_summary=entry.ai_output.get("output"),
                        )},
                    ]
                    result = ai_mgr.generate_insight({"messages": messages})
                    sent_count += 1
                    return {"ai": result}

                def reflect_and_push(entry, price):
                    out = reflect_cb(entry, price)
                    if push_enable and bots and out and out.get("ai"):
                        for b in bots:
                            b.send_markdown(
                                title="AI 反思",
                                text_md=(
                                    f"### AI 反思\n"
                                    f"- 标的: {entry.symbol}\n"
                                    f"- 动作: {entry.action}\n"
                                    f"- 当前价: {price}\n"
                                    f"- 目标: {entry.targets}\n"
                                    f"- 输出: {out['ai'].get('output')}\n"
                                ),
                            )
                    return out

                journal.refresh_progress(get_last_price, reflect_and_push)
            except Exception:
                pass
            await asyncio.sleep(300)

    loop.create_task(periodic_review())
    # 测试：可选触发一次策略信号，驱动 AI 与钉钉
    if os.environ.get("TEST_EMIT_SIGNAL", "0") == "1" and symbols:
        from datetime import datetime
        await event_mgr.emit_event(
            Event(
                event_type=EventType.STRATEGY_SIGNAL,
                data={
                    "strategy": "manual_test",
                    "symbol": symbols[0],
                    "action": "buy",
                    "qty": 1.0,
                    "price": 0.0,
                    "confidence": 0.99,
                    "reason": "manual_trigger",
                },
                timestamp=datetime.now(),
                source="manual_test",
            )
        )
    try:
        await runner.start(strategy, symbols=symbols)
    finally:
        await event_mgr.stop()


if __name__ == "__main__":
    asyncio.run(main())


