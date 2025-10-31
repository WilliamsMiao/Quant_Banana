from __future__ import annotations

import pandas as pd

from ...base_strategy import BaseStrategy, Signal


class MovingAverageCrossoverStrategy(BaseStrategy):
    def __init__(self, name: str = "ma_cross", config=None):
        super().__init__(name, config)
        self.fast = int((config or {}).get("fast", 5))
        self.slow = int((config or {}).get("slow", 20))

    def generate_signals(self, data: pd.DataFrame):
        if data.empty or len(data) < max(self.fast, self.slow) + 1:
            return []
        close = data["close"].astype(float)
        ma_fast = close.rolling(self.fast).mean()
        ma_slow = close.rolling(self.slow).mean()
        cross_up = ma_fast.iloc[-2] <= ma_slow.iloc[-2] and ma_fast.iloc[-1] > ma_slow.iloc[-1]
        cross_down = ma_fast.iloc[-2] >= ma_slow.iloc[-2] and ma_fast.iloc[-1] < ma_slow.iloc[-1]

        symbol = str(data["symbol"].iloc[-1])
        last_price = float(close.iloc[-1])

        signals = []
        if cross_up:
            signals.append(Signal(symbol=symbol, action="buy", quantity=1.0, price=last_price, confidence=0.7, reason="ma_cross_up"))
        elif cross_down:
            signals.append(Signal(symbol=symbol, action="sell", quantity=1.0, price=last_price, confidence=0.7, reason="ma_cross_down"))
        return signals

    def calculate_position_size(self, signal: Signal, current_price: float) -> float:
        return signal.quantity


