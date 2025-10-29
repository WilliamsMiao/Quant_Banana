"""
订单管理器
负责订单的创建、更新和状态管理
"""

from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """订单方向枚举"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """订单类型枚举"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class Order:
    """订单数据类"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    created_at: datetime = None
    updated_at: datetime = None
    strategy_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self._orders: Dict[str, Order] = {}
        self._order_history: List[Order] = []
    
    def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: float, price: Optional[float] = None,
                    stop_price: Optional[float] = None, strategy_id: Optional[str] = None) -> Order:
        """创建订单"""
        order_id = str(uuid.uuid4())
        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            strategy_id=strategy_id
        )
        
        self._orders[order_id] = order
        logger.info(f"创建订单: {order_id} - {symbol} {side.value} {quantity}")
        return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self._orders.get(order_id)
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """根据状态获取订单列表"""
        return [order for order in self._orders.values() if order.status == status]
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """根据策略ID获取订单列表"""
        return [order for order in self._orders.values() if order.strategy_id == strategy_id]
    
    def update_order_status(self, order_id: str, status: OrderStatus, 
                          filled_quantity: float = None, average_price: float = None):
        """更新订单状态"""
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"订单不存在: {order_id}")
            return
        
        order.status = status
        order.updated_at = datetime.now()
        
        if filled_quantity is not None:
            order.filled_quantity = filled_quantity
        if average_price is not None:
            order.average_price = average_price
        
        logger.info(f"更新订单状态: {order_id} - {status.value}")
        
        # 如果订单完成，移动到历史记录
        if status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            self._order_history.append(order)
            del self._orders[order_id]
    
    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"订单不存在: {order_id}")
            return False
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            logger.warning(f"订单已完成，无法撤销: {order_id}")
            return False
        
        self.update_order_status(order_id, OrderStatus.CANCELLED)
        logger.info(f"撤销订单: {order_id}")
        return True
    
    def get_all_orders(self) -> List[Order]:
        """获取所有活跃订单"""
        return list(self._orders.values())
    
    def get_order_history(self) -> List[Order]:
        """获取订单历史"""
        return self._order_history.copy()
