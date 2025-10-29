"""
交易相关类型定义
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PositionSide(Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"


class MarketType(Enum):
    """市场类型"""
    STOCK = "stock"
    OPTION = "option"
    FUTURE = "future"
    CRYPTO = "crypto"


@dataclass
class Order:
    """订单数据类"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal('0')
    average_price: Optional[Decimal] = None
    created_at: datetime = None
    updated_at: datetime = None
    strategy_id: Optional[str] = None
    client_order_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class Position:
    """持仓数据类"""
    symbol: str
    quantity: Decimal
    average_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal = Decimal('0')
    side: PositionSide = PositionSide.LONG
    market_type: MarketType = MarketType.STOCK
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class MarketData:
    """市场数据类"""
    symbol: str
    price: Decimal
    volume: int
    timestamp: datetime
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None
    close: Optional[Decimal] = None


@dataclass
class Trade:
    """成交数据类"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime
    strategy_id: Optional[str] = None


@dataclass
class AccountInfo:
    """账户信息类"""
    account_id: str
    total_value: Decimal
    cash: Decimal
    buying_power: Decimal
    margin_used: Decimal
    positions: List[Position]
    orders: List[Order]
    trades: List[Trade]
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now()
