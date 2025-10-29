"""
策略单元测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.strategies.base_strategy import BaseStrategy, Signal, OrderSide, OrderType


class TestStrategy(BaseStrategy):
    """测试策略"""
    
    def generate_signals(self, data: pd.DataFrame):
        """生成测试信号"""
        signals = []
        if len(data) > 0:
            signal = Signal(
                symbol="AAPL",
                action="buy",
                quantity=100,
                price=data['close'].iloc[-1],
                confidence=0.8,
                reason="测试信号"
            )
            signals.append(signal)
        return signals
    
    def calculate_position_size(self, signal: Signal, current_price: float) -> float:
        """计算仓位大小"""
        return signal.quantity


class TestBaseStrategy:
    """测试策略基类"""
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = TestStrategy("test_strategy")
        assert strategy.name == "test_strategy"
        assert not strategy.is_running
        assert len(strategy.positions) == 0
        assert len(strategy.signals) == 0
    
    def test_strategy_start_stop(self):
        """测试策略启动和停止"""
        strategy = TestStrategy("test_strategy")
        
        strategy.start()
        assert strategy.is_running
        
        strategy.stop()
        assert not strategy.is_running
    
    def test_signal_generation(self):
        """测试信号生成"""
        strategy = TestStrategy("test_strategy")
        
        # 创建测试数据
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'close': np.random.randn(10).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 10)
        }, index=dates)
        
        signals = strategy.generate_signals(data)
        assert len(signals) == 1
        assert signals[0].symbol == "AAPL"
        assert signals[0].action == "buy"
    
    def test_position_tracking(self):
        """测试持仓跟踪"""
        strategy = TestStrategy("test_strategy")
        
        # 模拟订单成交
        strategy.on_order_filled("order1", "AAPL", 100, 150.0)
        assert strategy.positions["AAPL"] == 100
        
        strategy.on_order_filled("order2", "AAPL", 50, 155.0)
        assert strategy.positions["AAPL"] == 150
    
    def test_config_update(self):
        """测试配置更新"""
        strategy = TestStrategy("test_strategy", {"param1": 10})
        
        new_config = {"param2": 20, "param1": 15}
        strategy.update_config(new_config)
        
        assert strategy.config["param1"] == 15
        assert strategy.config["param2"] == 20


if __name__ == "__main__":
    pytest.main([__file__])
