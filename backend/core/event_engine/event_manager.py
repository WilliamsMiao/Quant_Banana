"""
事件管理器
负责事件的注册、分发和处理
"""

from typing import Dict, List, Callable, Any
from enum import Enum
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    MARKET_DATA = "market_data"
    ORDER_UPDATE = "order_update"
    STRATEGY_SIGNAL = "strategy_signal"
    RISK_ALERT = "risk_alert"
    SYSTEM_EVENT = "system_event"


@dataclass
class Event:
    """事件数据类"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source: str


class EventManager:
    """事件管理器"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._event_queue = asyncio.Queue()
        self._running = False
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"注册事件处理器: {event_type.value}")
    
    def unregister_handler(self, event_type: EventType, handler: Callable):
        """注销事件处理器"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"注销事件处理器: {event_type.value}")
            except ValueError:
                logger.warning(f"处理器未找到: {event_type.value}")
    
    async def emit_event(self, event: Event):
        """发送事件"""
        await self._event_queue.put(event)
        logger.debug(f"发送事件: {event.event_type.value}")
    
    async def start(self):
        """启动事件管理器"""
        self._running = True
        logger.info("事件管理器已启动")
        
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"处理事件时出错: {e}")
    
    async def stop(self):
        """停止事件管理器"""
        self._running = False
        logger.info("事件管理器已停止")
    
    async def _process_event(self, event: Event):
        """处理事件"""
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"事件处理器执行失败: {e}")
