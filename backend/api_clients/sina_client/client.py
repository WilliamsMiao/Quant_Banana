"""
新浪财经API客户端
支持实时行情和历史数据获取
参考文档: https://www.sinacloud.com/doc/api.html
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


class SinaClient:
    """新浪财经API客户端"""
    
    # 新浪财经实时行情API（公开接口，无需认证）
    REAL_TIME_QUOTE_URL = "http://hq.sinajs.cn/list="
    
    # 新浪云API（如需要，使用SAE认证）
    SAE_BASE_URL = "https://g.sae.sina.com.cn"
    
    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        初始化新浪财经客户端
        
        Args:
            access_key: 新浪云AccessKey（如使用SAE API）
            secret_key: 新浪云SecretKey（如使用SAE API）
            timeout: 请求超时时间（秒）
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.timeout = timeout
    
    def get_realtime_quote(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        获取实时行情（公开接口，无需认证）
        
        Args:
            symbols: 标的代码列表（新浪格式，如 ["hk00700", "sh000001"]）
            
        Returns:
            标的代码到行情数据的映射
        """
        if not symbols:
            return {}
        
        try:
            # 新浪实时行情API：多个标的用逗号分隔
            symbol_str = ",".join(symbols)
            url = f"{self.REAL_TIME_QUOTE_URL}{symbol_str}"
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析响应（GBK编码）
            content = response.content.decode("gbk", errors="ignore")
            
            result: Dict[str, Dict[str, Any]] = {}
            lines = content.strip().split("\n")
            
            for line in lines:
                if not line or "=" not in line:
                    continue
                
                # 格式: var hq_str_hk00700="...";
                match = re.match(r'var\s+hq_str_(\w+)="([^"]+)"', line)
                if match:
                    symbol, data_str = match.groups()
                    quote_data = self._parse_quote_data(symbol, data_str)
                    if quote_data:
                        result[symbol] = quote_data
            
            return result
        except Exception as e:
            logger.error(f"获取新浪实时行情失败: {e}")
            return {}
    
    def _parse_quote_data(self, symbol: str, data_str: str) -> Optional[Dict[str, Any]]:
        """
        解析新浪行情数据字符串
        
        Args:
            symbol: 标的代码
            data_str: 行情数据字符串（逗号分隔）
            
        Returns:
            解析后的行情数据字典
        """
        try:
            fields = data_str.split(",")
            if len(fields) < 6:
                return None
            
            # 港股格式（示例，可能需要根据实际情况调整）:
            # 名称,今开,昨收,最新,最高,最低,成交量,成交额,时间
            # A股格式:
            # 名称,今开,昨收,最新,最高,最低,成交量,成交额,买一,买一量,卖一,卖一量,时间
            
            quote_data = {
                "symbol": symbol,
                "name": fields[0] if fields[0] else "",
                "open": float(fields[1]) if fields[1] and fields[1] != "" else 0.0,
                "prev_close": float(fields[2]) if len(fields) > 2 and fields[2] and fields[2] != "" else 0.0,
                "price": float(fields[3]) if len(fields) > 3 and fields[3] and fields[3] != "" else 0.0,
                "high": float(fields[4]) if len(fields) > 4 and fields[4] and fields[4] != "" else 0.0,
                "low": float(fields[5]) if len(fields) > 5 and fields[5] and fields[5] != "" else 0.0,
                "volume": float(fields[6]) if len(fields) > 6 and fields[6] and fields[6] != "" else 0.0,
                "amount": float(fields[7]) if len(fields) > 7 and fields[7] and fields[7] != "" else 0.0,
            }
            
            # 时间字段（如果有）
            if len(fields) > 8:
                time_str = fields[8].strip()
                quote_data["time"] = time_str
            
            return quote_data
        except Exception as e:
            logger.warning(f"解析新浪行情数据失败: {symbol}, {e}")
            return None
    
    def get_historical_kline(
        self,
        symbol: str,
        period: str = "day",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取历史K线数据
        注意：新浪财经的公开API主要提供实时行情，历史数据可能需要使用其他接口或数据源
        
        Args:
            symbol: 标的代码（新浪格式）
            period: K线周期（day/week/month）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            K线数据列表
        """
        # 新浪财经的公开实时行情API不提供历史数据
        # 如果需要历史数据，可能需要：
        # 1. 使用新浪云SAE API（需要认证）
        # 2. 或使用其他数据源（如AKShare）
        logger.warning("新浪财经公开API不提供历史K线数据，建议使用其他数据源")
        return []
    
    def _sae_authenticate(self, method: str, uri: str, params: Optional[Dict] = None) -> Dict[str, str]:
        """
        生成新浪云SAE API认证头
        参考: https://www.sinacloud.com/doc/api.html#签名方法
        
        Args:
            method: HTTP方法
            uri: 请求URI
            params: 请求参数
            
        Returns:
            认证头字典
        """
        if not self.access_key or not self.secret_key:
            raise ValueError("需要提供AccessKey和SecretKey以使用SAE API")
        
        import hmac
        import hashlib
        import base64
        import time
        
        timestamp = str(int(time.time()))
        
        # 构建签名原文
        headers_dict = {
            "x-sae-accesskey": self.access_key,
            "x-sae-timestamp": timestamp,
        }
        
        # 排序并拼接
        sorted_headers = sorted(headers_dict.items())
        header_str = "\n".join([f"{k}:{v}" for k, v in sorted_headers])
        
        # 签名原文 = method + uri + header_str
        sign_str = f"{method}\n{uri}\n{header_str}"
        
        # HMAC SHA256签名
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256
        ).digest()
        
        # Base64编码
        auth_token = base64.b64encode(signature).decode("utf-8")
        
        return {
            "x-sae-accesskey": self.access_key,
            "x-sae-timestamp": timestamp,
            "Authorization": f"SAEV1_HMAC_SHA256 {auth_token}",
        }

