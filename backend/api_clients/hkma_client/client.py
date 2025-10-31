"""
香港金管局API客户端
获取月度统计公报数据
参考文档: https://apidocs.hkma.gov.hk/chi/documentation/market-data-and-statistics/monthly-statistical-bulletin/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class HKMAClient:
    """香港金管局API客户端"""
    
    BASE_URL = "https://api.hkma.gov.hk"
    
    def __init__(self, timeout: int = 30):
        """
        初始化金管局客户端
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
    
    def get_monthly_statistics(
        self,
        indicator: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取月度统计数据
        
        Args:
            indicator: 指标名称（如 "base_rate", "usd_hkd_rate"等）
            year: 年份（可选）
            month: 月份（可选，1-12）
            
        Returns:
            统计数据列表
        """
        try:
            # 构建请求参数
            params: Dict[str, Any] = {}
            if indicator:
                params["indicator"] = indicator
            if year:
                params["year"] = year
            if month:
                params["month"] = month
            
            # 检查缓存（月度数据更新频率低，可以缓存）
            cache_key = f"{indicator}_{year}_{month}"
            if cache_key in self._cache:
                cache_time = self._cache_ttl.get(cache_key)
                if cache_time and (datetime.now() - cache_time).days < 1:
                    logger.debug(f"使用缓存数据: {cache_key}")
                    return self._cache[cache_key]
            
            # 构建API端点（需要根据实际API文档调整）
            # 示例端点，实际可能需要调整
            endpoint = "/public/market-data/monthly-statistics"
            url = f"{self.BASE_URL}{endpoint}"
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 缓存结果
            self._cache[cache_key] = data
            self._cache_ttl[cache_key] = datetime.now()
            
            return data if isinstance(data, list) else [data]
        except Exception as e:
            logger.error(f"获取金管局月度统计数据失败: {indicator}, {e}")
            return []
    
    def get_base_rate(self, year: Optional[int] = None, month: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取基准利率数据
        
        Args:
            year: 年份（可选）
            month: 月份（可选）
            
        Returns:
            基准利率数据列表
        """
        return self.get_monthly_statistics(indicator="base_rate", year=year, month=month)
    
    def get_exchange_rate(
        self,
        currency_pair: str = "USD_HKD",
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取汇率数据
        
        Args:
            currency_pair: 货币对（如 "USD_HKD"）
            year: 年份（可选）
            month: 月份（可选）
            
        Returns:
            汇率数据列表
        """
        return self.get_monthly_statistics(indicator=f"exchange_rate_{currency_pair}", year=year, month=month)
    
    def get_money_supply(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取货币供应量数据
        
        Args:
            year: 年份（可选）
            month: 月份（可选）
            
        Returns:
            货币供应量数据列表
        """
        return self.get_monthly_statistics(indicator="money_supply", year=year, month=month)

