from __future__ import annotations

import pandas as pd

from ...base_strategy import BaseStrategy, Signal


class IntradayVWAPReversionStrategy(BaseStrategy):
    def __init__(self, name: str = "intraday_vwap_reversion", config=None):
        super().__init__(name, config)
        cfg = config or {}
        self.deviation = float(cfg.get("deviation", 0.005))  # 0.5%
        self.min_volume = float(cfg.get("min_volume", 1000))

    def generate_signals(self, data: pd.DataFrame):
        if data.empty or len(data) < 10:
            return []
        df = data.copy()
        df["tp"] = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
        df["vwap_num"] = (df["tp"] * df["volume"].astype(float)).cumsum()
        df["vwap_den"] = df["volume"].astype(float).cumsum()
        df["vwap"] = df["vwap_num"] / df["vwap_den"].replace(0, pd.NA)
        last = df.iloc[-1]
        price = float(last["close"])
        vwap = float(last["vwap"]) if pd.notna(last["vwap"]) else price
        vol = float(last["volume"])
        symbol = str(last["symbol"]) if "symbol" in df.columns else "UNKNOWN"

        if vol < self.min_volume:
            return []

        signals = []
        if price < vwap * (1 - self.deviation):
            signals.append(Signal(symbol=symbol, action="buy", quantity=1.0, price=price, confidence=0.6, reason="below_vwap_revert"))
        elif price > vwap * (1 + self.deviation):
            signals.append(Signal(symbol=symbol, action="sell", quantity=1.0, price=price, confidence=0.6, reason="above_vwap_revert"))
        return signals

    def calculate_position_size(self, signal: Signal, current_price: float) -> float:
        return signal.quantity


