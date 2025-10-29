"""
策略基类
定义所有交易策略的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """交易信号数据类"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    quantity: float
    price: Optional[float] = None
    confidence: float = 1.0
    reason: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.is_running = False
        self.positions: Dict[str, float] = {}
        self.signals: List[Signal] = []
        self.performance_metrics: Dict[str, float] = {}
        
        logger.info(f"初始化策略: {name}")
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 市场数据DataFrame
            
        Returns:
            交易信号列表
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, current_price: float) -> float:
        """
        计算仓位大小
        
        Args:
            signal: 交易信号
            current_price: 当前价格
            
        Returns:
            建议仓位大小
        """
        pass
    
    def on_market_data(self, data: pd.DataFrame):
        """市场数据回调"""
        if not self.is_running:
            return
        
        try:
            signals = self.generate_signals(data)
            for signal in signals:
                self.signals.append(signal)
                logger.info(f"策略 {self.name} 生成信号: {signal.symbol} {signal.action}")
        except Exception as e:
            logger.error(f"策略 {self.name} 处理市场数据时出错: {e}")
    
    def on_order_filled(self, order_id: str, symbol: str, quantity: float, price: float):
        """订单成交回调"""
        if symbol in self.positions:
            self.positions[symbol] += quantity
        else:
            self.positions[symbol] = quantity
        
        logger.info(f"策略 {self.name} 订单成交: {symbol} {quantity} @ {price}")
    
    def start(self):
        """启动策略"""
        self.is_running = True
        logger.info(f"策略 {self.name} 已启动")
    
    def stop(self):
        """停止策略"""
        self.is_running = False
        logger.info(f"策略 {self.name} 已停止")
    
    def get_positions(self) -> Dict[str, float]:
        """获取当前持仓"""
        return self.positions.copy()
    
    def get_signals(self, limit: int = 100) -> List[Signal]:
        """获取最近的交易信号"""
        return self.signals[-limit:] if self.signals else []
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新策略配置"""
        self.config.update(new_config)
        logger.info(f"策略 {self.name} 配置已更新")
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取策略性能指标"""
        return self.performance_metrics.copy()
    
    def calculate_metrics(self, returns: pd.Series):
        """计算性能指标"""
        if len(returns) == 0:
            return
        
        # 计算基本指标
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = returns.std() * (252 ** 0.5)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # 计算最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        self.performance_metrics = {
            "total_return": total_return,
            "annual_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": (returns > 0).mean(),
            "avg_win": returns[returns > 0].mean() if (returns > 0).any() else 0,
            "avg_loss": returns[returns < 0].mean() if (returns < 0).any() else 0
        }
