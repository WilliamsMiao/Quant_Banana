from __future__ import annotations

import logging
import numpy as np
import pandas as pd

from ...base_strategy import BaseStrategy, Signal


class OptimizedHKIntradayStrategy(BaseStrategy):
    def __init__(self, name: str = "optimized_hk_intraday", config=None):
        super().__init__(name, config)
        self.logger = logging.getLogger(__name__)
        cfg = config or {}
        self.current_capital = float(cfg.get("initial_capital", 10000))
        # 动态本金配置
        self.capital_config = self.initialize_capital_config(self.current_capital)
        # 其他可调参数
        self.donchian_window = int(cfg.get("donchian_window", 20))

        # 交易状态
        self.daily_trade_count = 0
        self.daily_pnl = 0.0

        # 手续费参数（可按需放入配置）
        self.broker_config = {
            "commission_rate": 0.0003,  # 0.03%
            "min_commission": 3.0,      # 最低佣金 3 HKD
            "platform_fee": 1.0,        # 平台费
            "stamp_duty": 0.0013,       # 卖出印花税 0.13%
            "trading_levy": 0.000027,   # 交易征费
            "sfc_levy": 0.00005,        # 证监会征费
        }

    # ========= 动态本金相关 =========
    def initialize_capital_config(self, capital: float) -> dict:
        if capital <= 5000:
            return {
                "max_daily_trades": 2,
                "max_position_ratio": 0.25,
                "daily_stop_loss": 0.015,
                "trade_stop_loss": 0.01,
                "min_profit_after_cost": 0.008,
                "risk_reward_ratio": 1.8,
                "signal_strength_threshold": 65,
            }
        elif capital <= 20000:
            return {
                "max_daily_trades": 3,
                "max_position_ratio": 0.3,
                "daily_stop_loss": 0.02,
                "trade_stop_loss": 0.015,
                "min_profit_after_cost": 0.006,
                "risk_reward_ratio": 1.5,
                "signal_strength_threshold": 60,
            }
        else:
            return {
                "max_daily_trades": 5,
                "max_position_ratio": 0.4,
                "daily_stop_loss": 0.025,
                "trade_stop_loss": 0.02,
                "min_profit_after_cost": 0.005,
                "risk_reward_ratio": 1.3,
                "signal_strength_threshold": 55,
            }

    def update_capital(self, new_capital: float) -> None:
        self.current_capital = float(new_capital)
        self.capital_config = self.initialize_capital_config(self.current_capital)
        self.logger.info(f"本金更新为: {new_capital}HKD, 新配置: {self.capital_config}")

    # ========= 频率/费用/仓位 =========
    def calculate_dynamic_frequency(self, market_volatility: float | None = None) -> int:
        base_frequency = int(self.capital_config["max_daily_trades"])
        freq_adj = 1.0
        if market_volatility is not None:
            if market_volatility > 0.03:
                freq_adj = 0.7
            elif market_volatility < 0.01:
                freq_adj = 0.8
        if self.daily_pnl < -self.current_capital * 0.005:
            freq_adj *= 0.5
        return max(1, int(base_frequency * freq_adj))

    def calculate_transaction_cost(self, price: float, quantity: int, is_buy: bool = True) -> float:
        amount = float(price) * float(quantity)
        commission = max(amount * self.broker_config["commission_rate"], self.broker_config["min_commission"])
        stamp_duty = amount * self.broker_config["stamp_duty"] if not is_buy else 0.0
        trading_levy = amount * self.broker_config["trading_levy"]
        sfc_levy = amount * self.broker_config["sfc_levy"]
        platform_fee = self.broker_config["platform_fee"]
        total = commission + stamp_duty + trading_levy + sfc_levy + platform_fee
        return round(total, 2)

    def calculate_optimal_position(self, current_price: float, stop_loss_price: float, signal_strength: float) -> tuple[int, str]:
        risk_per_trade = self.current_capital * self.capital_config["trade_stop_loss"]
        price_risk = abs(current_price - stop_loss_price)
        if price_risk <= 0:
            return 0, "价格风险为0"
        risk_based_qty = int(risk_per_trade / price_risk)
        capital_based_qty = int((self.current_capital * self.capital_config["max_position_ratio"]) / current_price)
        strength_multiplier = float(signal_strength) / 100.0
        strength_adjusted_qty = int(risk_based_qty * strength_multiplier)
        qty = min(risk_based_qty, capital_based_qty, strength_adjusted_qty)
        # 成本效益检查（双边）
        estimated_profit = abs(current_price * self.capital_config["min_profit_after_cost"] * qty)
        estimated_cost = self.calculate_transaction_cost(current_price, qty, True) * 2
        if estimated_profit <= estimated_cost * 1.5:
            return 0, f"预期盈利{estimated_profit:.2f}不足覆盖成本{estimated_cost:.2f}"
        # 资金充足性
        total_cost = current_price * qty + estimated_cost
        if total_cost > self.current_capital * 0.9:
            affordable_qty = int((self.current_capital * 0.9 - estimated_cost) / current_price)
            qty = max(0, min(qty, affordable_qty))
        return max(0, qty), "计算成功"

    # ========= 多时间框架与指标 =========
    def multi_timeframe_analysis(self, df: pd.DataFrame) -> dict:
        analysis: dict = {}
        close = df["close"].astype(float)
        vol = df["volume"].astype(float)
        analysis["rsi_14"] = self.calculate_rsi(close, 14)
        analysis["volume_ma_ratio"] = vol / vol.rolling(10).mean()
        analysis["price_trend"] = self.assess_trend(close)
        analysis["volatility"] = close.pct_change().std() * np.sqrt(252)
        analysis["support_resistance"] = self.find_support_resistance(df)
        return analysis

    def assess_trend(self, prices: pd.Series, short_window: int = 5, long_window: int = 20) -> str:
        short_ma = prices.rolling(short_window).mean()
        long_ma = prices.rolling(long_window).mean()
        if short_ma.iloc[-1] > long_ma.iloc[-1] and prices.iloc[-1] > short_ma.iloc[-1]:
            return "strong_uptrend"
        elif short_ma.iloc[-1] > long_ma.iloc[-1]:
            return "weak_uptrend"
        elif short_ma.iloc[-1] < long_ma.iloc[-1] and prices.iloc[-1] < short_ma.iloc[-1]:
            return "strong_downtrend"
        else:
            return "weak_downtrend"

    def find_support_resistance(self, df: pd.DataFrame, window: int = 10) -> dict:
        high = df["high"].astype(float).tail(window).max()
        low = df["low"].astype(float).tail(window).min()
        current_price = float(df["close"].astype(float).iloc[-1])
        return {
            "resistance": high,
            "support": low,
            "distance_to_resistance": (high - current_price) / current_price if current_price else 0.0,
            "distance_to_support": (current_price - low) / current_price if current_price else 0.0,
        }

    # ========= 信号生成 =========
    def enhanced_donchian_strategy(self, df: pd.DataFrame, window: int) -> list[dict]:
        df = df.copy()
        df["upper_band"] = df["high"].astype(float).rolling(window=window).max()
        df["lower_band"] = df["low"].astype(float).rolling(window=window).min()
        market_analysis = self.multi_timeframe_analysis(df)
        signals: list[dict] = []
        for i in range(window, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i - 1]
            long_break = current["close"] > prev["upper_band"]
            short_break = current["close"] < prev["lower_band"]
            if not (long_break or short_break):
                continue
            direction = "long" if long_break else "short"
            signal_strength = self.calculate_enhanced_signal_strength(current, direction, market_analysis, i)
            if signal_strength < self.capital_config["signal_strength_threshold"]:
                continue
            stop_loss, take_profit = self.calculate_enhanced_risk_levels(current["close"], direction, market_analysis)
            position_size, position_reason = self.calculate_optimal_position(current["close"], stop_loss, signal_strength)
            if position_size <= 0:
                continue
            expected_profit = abs(take_profit - current["close"]) * position_size
            expected_cost = self.calculate_transaction_cost(current["close"], position_size, True)
            cost_ratio = (expected_profit / expected_cost) if expected_cost > 0 else 0
            signals.append(
                {
                    "timestamp": current.name,
                    "symbol": "HK",
                    "action": "BUY" if direction == "long" else "SELL",
                    "reason": self.generate_signal_reason(current, direction, prev, market_analysis),
                    "current_price": float(current["close"]),
                    "signal_strength": float(signal_strength),
                    "position_size": int(position_size),
                    "position_reason": position_reason,
                    "stop_loss": float(stop_loss),
                    "take_profit": float(take_profit),
                    "risk_reward_ratio": abs(take_profit - current["close"]) / max(abs(current["close"] - stop_loss), 1e-8),
                    "cost_ratio": float(cost_ratio),
                    "market_volatility": float(market_analysis["volatility"]),
                    "trend_strength": str(market_analysis["price_trend"]),
                    "rsi": float(market_analysis["rsi_14"].iloc[i]),
                    "volume_ratio": float(market_analysis["volume_ma_ratio"].iloc[i]),
                    "support_resistance": market_analysis["support_resistance"],
                    "bars_analyzed": int(window),
                    "dynamic_frequency": int(self.calculate_dynamic_frequency(market_analysis["volatility"])),
                }
            )
        return signals

    def calculate_enhanced_signal_strength(self, current: pd.Series, direction: str, market_analysis: dict, index: int) -> int:
        strength = 50
        rsi = market_analysis["rsi_14"].iloc[index]
        if direction == "long":
            if rsi < 30:
                strength += 15
            elif rsi > 70:
                strength -= 15
        else:
            if rsi > 70:
                strength += 15
            elif rsi < 30:
                strength -= 15
        volume_ratio = market_analysis["volume_ma_ratio"].iloc[index]
        if volume_ratio > 1.8:
            strength += 15
        elif volume_ratio > 1.3:
            strength += 10
        elif volume_ratio < 0.7:
            strength -= 10
        trend = market_analysis["price_trend"]
        if (direction == "long" and "uptrend" in trend) or (direction == "short" and "downtrend" in trend):
            strength += 20
        elif (direction == "long" and "downtrend" in trend) or (direction == "short" and "uptrend" in trend):
            strength -= 15
        sr = market_analysis["support_resistance"]
        if direction == "long" and sr["distance_to_resistance"] > 0.03:
            strength += 10
        if direction == "short" and sr["distance_to_support"] > 0.03:
            strength += 10
        volatility = market_analysis["volatility"]
        if 0.01 <= volatility <= 0.03:
            strength += 10
        elif volatility > 0.05:
            strength -= 10
        if direction == "long":
            breakout_strength = (current["close"] - current["upper_band"]) / max(current["upper_band"], 1e-8)
        else:
            breakout_strength = (current["lower_band"] - current["close"]) / max(current["lower_band"], 1e-8)
        if breakout_strength > 0.01:
            strength += 20
        elif breakout_strength > 0.005:
            strength += 10
        elif breakout_strength < 0.001:
            strength -= 10
        return int(max(0, min(100, strength)))

    def calculate_enhanced_risk_levels(self, current_price: float, direction: str, market_analysis: dict) -> tuple[float, float]:
        base_sl = self.capital_config["trade_stop_loss"]
        base_rr = self.capital_config["risk_reward_ratio"]
        vol = market_analysis["volatility"]
        if vol > 0.03:
            sl_adj = 1.2
        elif vol < 0.01:
            sl_adj = 0.8
        else:
            sl_adj = 1.0
        adjusted_sl = base_sl * sl_adj
        if direction == "long":
            stop_loss = current_price * (1 - adjusted_sl)
            take_profit = current_price * (1 + adjusted_sl * base_rr)
        else:
            stop_loss = current_price * (1 + adjusted_sl)
            take_profit = current_price * (1 - adjusted_sl * base_rr)
        sr = market_analysis["support_resistance"]
        if direction == "long" and stop_loss < sr["support"]:
            stop_loss = sr["support"] * 0.995
        if direction == "short" and stop_loss > sr["resistance"]:
            stop_loss = sr["resistance"] * 1.005
        return float(stop_loss), float(take_profit)

    # ========= 指标与信号桥接 =========
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signal_reason(self, current: pd.Series, direction: str, prev: pd.Series, ma: dict) -> str:
        reasons = []
        if direction == "long":
            reasons.append(f"价格{current['close']:.2f}突破上轨{prev['upper_band']:.2f}")
        else:
            reasons.append(f"价格{current['close']:.2f}跌破下轨{prev['lower_band']:.2f}")
        rsi_val = ma["rsi_14"].iloc[-1]
        if (direction == "long" and rsi_val < 40) or (direction == "short" and rsi_val > 60):
            reasons.append(f"RSI({rsi_val:.1f})提供确认")
        vol_ratio = ma["volume_ma_ratio"].iloc[-1]
        if vol_ratio > 1.5:
            reasons.append(f"成交量放大{vol_ratio:.1f}倍")
        trend = ma["price_trend"]
        if (direction == "long" and "uptrend" in trend) or (direction == "short" and "downtrend" in trend):
            reasons.append("趋势方向一致")
        return "; ".join(reasons)

    # 核心：供 Runner 调用
    def generate_signals(self, data: pd.DataFrame):
        if data.empty or len(data) < max(30, self.donchian_window + 1):
            return []
        # 频率限制检查（可基于 self.daily_trade_count 与 dynamic_frequency 做限制，这里只生成信号，执行层控制频次）
        signals = self.enhanced_donchian_strategy(data, self.donchian_window)
        if not signals:
            return []
        # 取最新一个信号转为标准 Signal
        s = signals[-1]
        action = "buy" if s["action"].upper() == "BUY" else "sell"
        symbol = str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "HK"
        sig = Signal(
            symbol=symbol,
            action=action,
            quantity=float(s["position_size"]),
            price=float(s["current_price"]),
            confidence=min(1.0, max(0.0, s["signal_strength"] / 100.0)),
            reason=s.get("reason", "optimized_intraday"),
        )
        return [sig]

    def calculate_position_size(self, signal: Signal, current_price: float) -> float:
        return signal.quantity


