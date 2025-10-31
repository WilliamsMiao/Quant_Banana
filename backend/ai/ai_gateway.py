from __future__ import annotations

from typing import Any, Dict

from core.event_engine.event_manager import Event, EventManager, EventType
from ai.api_manager import AIAPIManager
from ai.prompt_manager import PromptManager


class AIGateway:
    def __init__(self, api_mgr: AIAPIManager, prompt_mgr: PromptManager, event_mgr: EventManager):
        self.api_mgr = api_mgr
        self.prompt_mgr = prompt_mgr
        self.event_mgr = event_mgr

    async def on_event(self, event: Event) -> None:
        if event.event_type not in (EventType.MARKET_DATA, EventType.STRATEGY_SIGNAL):
            return
        req: Dict[str, Any] = {"event": event.event_type.value, "data": event.data}
        _ = self.api_mgr.generate_insight(req)
        # 占位：暂不回写事件，只是消费


