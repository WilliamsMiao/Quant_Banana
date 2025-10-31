"""
交易时间管理模块
支持港股、美股、A股（预留）的交易时间判断和节假日判断
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional, Tuple

import pytz

try:
    import exchange_calendars as ec
    HAS_EXCHANGE_CALENDARS = True
except ImportError:
    HAS_EXCHANGE_CALENDARS = False
    logging.warning("exchange_calendars未安装，节假日判断将使用简化逻辑")


class MarketType(Enum):
    """市场类型枚举"""
    HK = "HK"  # 港股
    US = "US"  # 美股
    CN = "CN"  # A股


class TradingHoursManager:
    """交易时间管理器"""
    
    def __init__(self, market: str = "HK", timezone: str = "Asia/Hong_Kong", enable_holiday_check: bool = True):
        """
        初始化交易时间管理器
        
        Args:
            market: 市场类型 (HK/US/CN)
            timezone: 时区字符串，如 "Asia/Hong_Kong"
            enable_holiday_check: 是否启用节假日检查
        """
        self.market = MarketType(market.upper())
        self.tz = pytz.timezone(timezone)
        self.enable_holiday_check = enable_holiday_check and HAS_EXCHANGE_CALENDARS
        self.logger = logging.getLogger(__name__)
        
        # 初始化交易日历（如果支持）
        self.calendar = None
        if self.enable_holiday_check:
            try:
                if self.market == MarketType.HK:
                    self.calendar = ec.get_calendar("XHKG")  # 港股交易所日历
                elif self.market == MarketType.US:
                    self.calendar = ec.get_calendar("XNYS")  # 纽交所日历
                elif self.market == MarketType.CN:
                    self.calendar = ec.get_calendar("XSHG")  # 上交所日历
            except Exception as e:
                self.logger.warning(f"无法加载交易日历: {e}，将使用简化逻辑")
                self.enable_holiday_check = False
    
    def _get_now(self) -> datetime:
        """获取当前时间（使用配置的时区）"""
        return datetime.now(self.tz)
    
    def _get_market_trading_hours(self) -> Tuple[time, time, Optional[time], Optional[time]]:
        """
        获取市场的交易时间
        
        Returns:
            (早盘开始, 早盘结束, 午盘开始, 午盘结束)
            如果只有一段交易时间，午盘开始和结束为None
        """
        if self.market == MarketType.HK:
            # 港股：09:30-12:00, 13:00-16:00 HKT
            return (time(9, 30), time(12, 0), time(13, 0), time(16, 0))
        elif self.market == MarketType.US:
            # 美股：09:30-16:00 ET（预留）
            return (time(9, 30), time(16, 0), None, None)
        elif self.market == MarketType.CN:
            # A股：09:30-11:30, 13:00-15:00 CST（预留）
            return (time(9, 30), time(11, 30), time(13, 0), time(15, 0))
        else:
            raise ValueError(f"不支持的市场类型: {self.market}")
    
    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """
        判断指定日期是否为交易日（排除节假日）
        
        Args:
            date: 要判断的日期，如果为None则使用今天
        
        Returns:
            是否为交易日
        """
        if date is None:
            date = self._get_now()
        
        # 转换为日期对象（移除时间部分）
        check_date = date.date()
        
        # 如果启用了节假日检查且交易日历可用
        if self.enable_holiday_check and self.calendar:
            try:
                # 检查是否为交易日
                is_open = self.calendar.is_session(check_date)
                return is_open
            except Exception as e:
                self.logger.warning(f"交易日历检查失败: {e}，使用简化逻辑")
        
        # 简化逻辑：检查是否为周末
        weekday = check_date.weekday()  # 0=Monday, 6=Sunday
        if weekday >= 5:  # Saturday (5) or Sunday (6)
            return False
        
        # 如果不是周末，默认是交易日（无法判断节假日时）
        return True
    
    def is_trading_time(self, check_time: Optional[datetime] = None) -> bool:
        """
        判断指定时间是否在交易时间内
        
        Args:
            check_time: 要判断的时间，如果为None则使用当前时间
        
        Returns:
            是否在交易时间内
        """
        if check_time is None:
            check_time = self._get_now()
        
        # 首先检查是否为交易日
        if not self.is_trading_day(check_time):
            return False
        
        # 获取交易时间
        morning_start, morning_end, afternoon_start, afternoon_end = self._get_market_trading_hours()
        
        # 获取当前时间（本地时区）
        current_time = check_time.time()
        
        # 检查是否在早盘交易时间
        if morning_start <= current_time <= morning_end:
            return True
        
        # 检查是否在午盘交易时间（如果有）
        if afternoon_start and afternoon_end:
            if afternoon_start <= current_time <= afternoon_end:
                return True
        
        return False
    
    def get_open_time_today(self) -> Optional[datetime]:
        """
        获取今日开盘时间
        
        Returns:
            今日开盘时间，如果是非交易日则返回None
        """
        now = self._get_now()
        if not self.is_trading_day(now):
            return None
        
        morning_start, _, _, _ = self._get_market_trading_hours()
        dt = datetime.combine(now.date(), morning_start)
        # 如果datetime已经是aware的，直接返回；否则本地化
        if dt.tzinfo is None:
            return self.tz.localize(dt)
        else:
            return dt
    
    def get_close_time_today(self) -> Optional[datetime]:
        """
        获取今日收盘时间
        
        Returns:
            今日收盘时间，如果是非交易日则返回None
        """
        now = self._get_now()
        if not self.is_trading_day(now):
            return None
        
        _, morning_end, afternoon_start, afternoon_end = self._get_market_trading_hours()
        
        # 如果只有一段交易时间
        if not afternoon_end:
            dt = datetime.combine(now.date(), morning_end)
        else:
            # 如果有午盘，返回午盘结束时间
            dt = datetime.combine(now.date(), afternoon_end)
        
        # 如果datetime已经是aware的，直接返回；否则本地化
        if dt.tzinfo is None:
            return self.tz.localize(dt)
        else:
            return dt
    
    def get_next_open_time(self) -> datetime:
        """
        获取下一个开盘时间
        
        Returns:
            下一个开盘时间
        """
        now = self._get_now()
        morning_start, _, _, _ = self._get_market_trading_hours()
        
        # 尝试找到下一个交易日
        for days_ahead in range(0, 10):  # 最多查找10天
            check_date = now.date() + timedelta(days=days_ahead)
            dt = datetime.combine(check_date, morning_start)
            if dt.tzinfo is None:
                check_datetime = self.tz.localize(dt)
            else:
                check_datetime = dt
            
            if self.is_trading_day(check_datetime):
                # 如果是今天且当前时间早于开盘时间，返回今天开盘时间
                if days_ahead == 0 and now.time() < morning_start:
                    return check_datetime
                # 否则返回下一个交易日的开盘时间
                elif days_ahead > 0:
                    return check_datetime
        
        # 如果找不到（理论上不应该），返回明天
        dt = datetime.combine(now.date() + timedelta(days=1), morning_start)
        if dt.tzinfo is None:
            return self.tz.localize(dt)
        else:
            return dt
    
    def should_auto_start(self, minutes_before: int = 10) -> bool:
        """
        判断是否应该自动启动（开盘前几分钟）
        
        Args:
            minutes_before: 开盘前几分钟
        
        Returns:
            是否应该自动启动
        """
        now = self._get_now()
        
        # 如果不是交易日，不启动
        if not self.is_trading_day(now):
            return False
        
        open_time = self.get_open_time_today()
        if open_time is None:
            return False
        
        # 计算开盘前几分钟的时间点
        auto_start_time = open_time - timedelta(minutes=minutes_before)
        
        # 当前时间是否在自动启动时间点和开盘时间之间
        return auto_start_time <= now < open_time
    
    def get_seconds_until_open(self) -> float:
        """
        获取距离开盘的秒数
        
        Returns:
            距离开盘的秒数（如果是非交易日或已开盘，返回0）
        """
        now = self._get_now()
        
        # 如果已经在交易时间内，返回0
        if self.is_trading_time(now):
            return 0.0
        
        # 获取今日开盘时间
        open_time_today = self.get_open_time_today()
        if open_time_today and open_time_today > now:
            return (open_time_today - now).total_seconds()
        
        # 如果今日已过或非交易日，获取下一个开盘时间
        next_open = self.get_next_open_time()
        return max(0.0, (next_open - now).total_seconds())
    
    def get_seconds_until_close(self) -> float:
        """
        获取距离收盘的秒数
        
        Returns:
            距离收盘的秒数（如果已收盘或非交易日，返回0）
        """
        now = self._get_now()
        
        # 如果不在交易时间内，返回0
        if not self.is_trading_time(now):
            return 0.0
        
        close_time = self.get_close_time_today()
        if close_time and close_time > now:
            return (close_time - now).total_seconds()
        
        return 0.0
    
    def get_seconds_until_auto_stop(self, minutes_after_close: int = 10) -> float:
        """
        获取距离自动停止的秒数（收盘后几分钟）
        
        Args:
            minutes_after_close: 收盘后几分钟停止
        
        Returns:
            距离自动停止的秒数（如果已到或未到收盘时间，返回相应值）
        """
        now = self._get_now()
        close_time = self.get_close_time_today()
        
        if close_time is None:
            return 0.0
        
        auto_stop_time = close_time + timedelta(minutes=minutes_after_close)
        
        if auto_stop_time <= now:
            return 0.0  # 已到停止时间
        
        return (auto_stop_time - now).total_seconds()

