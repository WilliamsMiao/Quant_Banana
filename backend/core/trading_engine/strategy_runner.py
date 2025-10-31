"""
策略运行器：
- 管理策略生命周期
- 拉取/订阅市场数据并推送给策略
- 将策略信号桥接到订单管理或事件总线
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal
from core.event_engine.event_manager import Event, EventManager, EventType
from core.trading_engine.order_manager import OrderManager
from data.market_data.interfaces import MarketDataProvider, SubscribeParams
from data.cache.market_cache import MarketCache


logger = logging.getLogger(__name__)


class StrategyRunner:
    def __init__(
        self,
        provider: MarketDataProvider,
        event_mgr: EventManager,
        order_mgr: OrderManager,
        market_cache: MarketCache,
        period: str = "1m",
        pull_interval_sec: float = 2.0,
        lookback: int = 200,
    ):
        self.provider = provider
        self.event_mgr = event_mgr
        self.order_mgr = order_mgr
        self.market_cache = market_cache
        self.period = period
        self.pull_interval_sec = pull_interval_sec
        self.lookback = lookback
        self._running = False

    async def start(self, strategy: BaseStrategy, symbols: List[str]) -> None:
        logger.info(f"启动策略运行器: {strategy.name}, symbols={symbols}, period={self.period}")
        self.provider.connect()
        self.provider.subscribe(SubscribeParams(symbols=symbols, period=self.period))
        strategy.start()
        self._running = True

        try:
            while self._running:
                for sym in symbols:
                    bars = self.provider.fetch_bars(sym, self.period, self.lookback)
                    self.market_cache.put_bars(sym, bars)
                    df = _bars_to_df(bars)
                    # 观测日志：打印最近一根K线与VWAP
                    if not df.empty:
                        try:
                            tp = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
                            vwap = (tp * df["volume"].astype(float)).cumsum() / df["volume"].astype(float).cumsum()
                            last = df.iloc[-1]
                            logger.info(
                                f"{sym} last close={float(last['close']):.4f}, vwap={float(vwap.iloc[-1]):.4f}, ts={last['start']}"
                            )
                        except Exception:
                            pass
                    strategy.on_market_data(df)
                    await self._handle_signals(strategy)
                    await self._emit_market_event(sym, df)
                await asyncio.sleep(self.pull_interval_sec)
        finally:
            strategy.stop()
            self.provider.close()
            self._running = False
            logger.info("策略运行器已停止")

    async def stop(self) -> None:
        self._running = False

    async def _handle_signals(self, strategy: BaseStrategy) -> None:
        signals = strategy.get_signals(limit=10)
        if not signals:
            return
        
        # 去重：只处理新的信号（基于 symbol+action，60秒内不重复）
        # 使用时间窗口缓存来避免重复处理相同信号
        import time
        if not hasattr(self, '_processed_signals'):
            self._processed_signals = {}  # {(symbol, action): last_emitted_timestamp}
        
        current_time = time.time()
        SIGNAL_COOLDOWN_SEC = 60.0  # 60秒冷却期
        
        # 清理过期缓存
        expired_keys = [k for k, v in self._processed_signals.items() 
                       if current_time - v > SIGNAL_COOLDOWN_SEC * 2]
        for k in expired_keys:
            del self._processed_signals[k]
        
        new_signals = []
        for sig in signals:
            # 只基于标的和方向去重，不包含timestamp
            key = (sig.symbol, sig.action)
            if key in self._processed_signals:
                last_time = self._processed_signals[key]
                elapsed = current_time - last_time
                if elapsed < SIGNAL_COOLDOWN_SEC:
                    logger.debug(f"[信号去重] 跳过重复信号: {sig.symbol} {sig.action}，距离上次仅 {elapsed:.1f}秒")
                    continue  # 跳过这个信号
            
            # 新信号或冷却期已过
            self._processed_signals[key] = current_time
            new_signals.append(sig)
            # 限制缓存大小，只保留最近100个
            if len(self._processed_signals) > 100:
                # 删除最旧的
                oldest_key = min(self._processed_signals.items(), key=lambda x: x[1])[0]
                del self._processed_signals[oldest_key]
        
        # 只发送新信号
        for sig in new_signals:
            await self.event_mgr.emit_event(
                Event(
                    event_type=EventType.STRATEGY_SIGNAL,
                    data={
                        "strategy": strategy.name,
                        "symbol": sig.symbol,
                        "action": sig.action,
                        "qty": sig.quantity,
                        "price": sig.price,
                        "confidence": sig.confidence,
                        "reason": sig.reason,
                    },
                    timestamp=sig.timestamp,
                    source="strategy_runner",
                )
            )
        
        # 清空策略的信号队列（防止重复发送）
        strategy.clear_signals()

    async def _emit_market_event(self, symbol: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        last = df.iloc[-1]
        await self.event_mgr.emit_event(
            Event(
                event_type=EventType.MARKET_DATA,
                data={
                    "symbol": symbol,
                    "close": float(last["close"]),
                    "ts": str(last["start"]),
                },
                timestamp=last["start"],
                source="strategy_runner",
            )
        )


def _bars_to_df(bars) -> pd.DataFrame:
    if not bars:
        return pd.DataFrame(columns=["start", "open", "high", "low", "close", "volume", "symbol"])
    rows = [
        {
            "symbol": b.symbol,
            "start": b.start,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in bars
    ]
    df = pd.DataFrame(rows)
    df.sort_values("start", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


