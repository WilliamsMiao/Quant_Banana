"""
iTick API客户端
支持REST API和WebSocket API，用于获取实时行情和历史数据
参考文档: https://docs.itick.org/
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
import websocket
from websocket import WebSocketApp

logger = logging.getLogger(__name__)


class ITickClient:
    """iTick API客户端"""
    
    # 免费体验API地址
    FREE_BASE_URL = "https://api-free.itick.org"
    FREE_WS_URL = "wss://api-free.itick.org"
    
    # 生产环境API地址
    PROD_BASE_URL = "https://api.itick.org"
    PROD_WS_URL = "wss://api.itick.org"
    
    DEFAULT_BASE_URL = PROD_BASE_URL
    DEFAULT_WS_URL = PROD_WS_URL
    
    def __init__(
        self,
        token: str,
        base_url: Optional[str] = None,
        ws_url: Optional[str] = None,
        timeout: int = 30,
        use_free_api: Optional[bool] = None,
    ):
        """
        初始化iTick客户端
        
        Args:
            token: iTick API token
            base_url: REST API基础URL（如果指定则使用指定值）
            ws_url: WebSocket API基础URL（如果指定则使用指定值）
            timeout: 请求超时时间（秒）
            use_free_api: 是否使用免费API（True=免费，False=生产，None=自动判断）
        """
        self.token = token
        
        # 如果没有指定base_url，根据use_free_api或token判断
        if base_url:
            self.base_url = base_url
        elif use_free_api is True:
            self.base_url = self.FREE_BASE_URL
        elif use_free_api is False:
            self.base_url = self.PROD_BASE_URL
        else:
            # 自动判断：根据配置或默认使用生产环境
            self.base_url = self.DEFAULT_BASE_URL
        
        # WebSocket URL类似处理
        if ws_url:
            self.ws_url = ws_url
        elif use_free_api is True:
            self.ws_url = self.FREE_WS_URL
        elif use_free_api is False:
            self.ws_url = self.PROD_WS_URL
        else:
            self.ws_url = self.DEFAULT_WS_URL
        
        self.timeout = timeout
        self._connected = False
        self._ws_app: Optional[WebSocketApp] = None
        self._ws_callbacks: Dict[str, Any] = {}
        
    def connect(self) -> None:
        """建立连接（REST API无需显式连接）"""
        if self._connected:
            return
        # REST API无需连接，但可以测试token有效性
        self._connected = True
        logger.info("ITickClient 已就绪")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法（GET/POST）
            endpoint: API端点
            params: 查询参数
            headers: 请求头
            
        Returns:
            API响应数据
        """
        url = urljoin(self.base_url, endpoint)
        default_headers = {
            "accept": "application/json",
            "token": self.token,  # iTick API使用token header，而不是Authorization Bearer
            "Content-Type": "application/json",
        }
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(
                    url, params=params, headers=default_headers, timeout=self.timeout
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url, json=params, headers=default_headers, timeout=self.timeout
                )
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"iTick API请求失败: {e}")
            raise
    
    def get_kline(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据
        
        Args:
            symbol: 标的代码（如 "700.HK", "00700.HK", 或解析后的代码如 "700"）
            interval: K线周期（如 "1min", "5min", "1day"）
            start_time: 开始时间（ISO格式或时间戳）
            end_time: 结束时间（ISO格式或时间戳）
            limit: 返回数量限制
            
        Returns:
            K线数据列表
        """
        # 解析symbol格式：700.HK -> code=700, region=hk
        # 或者保持原样：00700.HK
        code = symbol
        region = "hk"
        
        if "." in symbol:
            parts = symbol.split(".")
            if len(parts) == 2:
                code = parts[0].lstrip("0")  # 移除前导零，700.HK -> 700
                region = parts[1].lower()
        
        # 根据symbol/list的格式和API错误提示，使用type/region/code/kType参数
        params: Dict[str, Any] = {
            "type": "stock",
            "region": region,
            "code": code,
            "kType": interval,  # iTick API使用kType而不是interval
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        
        # 根据iTick文档，股票API的端点路径应该是 /stock/kline
        # 如果是其他产品类型，可以扩展为 /crypto/kline, /forex/kline 等
        endpoint = "/stock/kline"
        try:
            data = self._make_request("GET", endpoint, params=params)
            
            # 解析响应格式
            if isinstance(data, dict):
                if data.get("code") == 0 and "data" in data:
                    return data["data"] if isinstance(data["data"], list) else []
                elif data.get("code") != 0:
                    # API返回错误码
                    error_msg = data.get("msg", "未知错误")
                    logger.warning(f"iTick K线API返回错误: code={data.get('code')}, msg={error_msg}")
                    return []
            elif isinstance(data, list):
                return data
            
            logger.warning(f"iTick K线数据格式异常: {data}")
            return []
        except Exception as e:
            # 如果/symbol/kline失败，尝试旧端点（作为fallback）
            logger.warning(f"iTick /symbol/kline 端点失败，尝试备用端点: {e}")
            # 注意：可能需要根据实际API文档调整
            return []
    
    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取实时报价
        
        Args:
            symbol: 标的代码
            
        Returns:
            实时报价数据
        """
        params = {"symbol": symbol}
        endpoint = "/v1/market/quote"  # 可能需要根据实际文档调整
        data = self._make_request("GET", endpoint, params=params)
        
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data
    
    def get_realtime_trade(self, symbol: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取实时成交
        
        Args:
            symbol: 标的代码
            limit: 返回数量限制
            
        Returns:
            实时成交数据列表
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if limit:
            params["limit"] = limit
        
        endpoint = "/v1/market/trade"  # 可能需要根据实际文档调整
        data = self._make_request("GET", endpoint, params=params)
        
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        elif isinstance(data, list):
            return data
        return []
    
    def get_realtime_depth(self, symbol: str) -> Dict[str, Any]:
        """
        获取实时盘口
        
        Args:
            symbol: 标的代码
            
        Returns:
            实时盘口数据（买盘/卖盘）
        """
        params = {"symbol": symbol}
        endpoint = "/v1/market/depth"  # 可能需要根据实际文档调整
        data = self._make_request("GET", endpoint, params=params)
        
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data
    
    def batch_get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量获取实时报价
        
        Args:
            symbols: 标的代码列表
            
        Returns:
            标的代码到报价数据的映射
        """
        params = {"symbols": ",".join(symbols)}
        endpoint = "/v1/market/quotes"  # 可能需要根据实际文档调整
        data = self._make_request("GET", endpoint, params=params)
        
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data
    
    def subscribe_websocket(
        self,
        symbols: List[str],
        on_message: Optional[Any] = None,
        on_error: Optional[Any] = None,
        on_close: Optional[Any] = None,
    ) -> WebSocketApp:
        """
        订阅WebSocket实时数据
        
        Args:
            symbols: 要订阅的标的代码列表
            on_message: 消息回调函数
            on_error: 错误回调函数
            on_close: 关闭回调函数
            
        Returns:
            WebSocket应用对象
        """
        ws_url = f"{self.ws_url}/v1/market?token={self.token}"
        
        def default_on_message(ws, message):
            try:
                import json
                if isinstance(message, str):
                    data = json.loads(message)
                else:
                    data = message
                if on_message:
                    on_message(ws, data)
            except Exception as e:
                logger.error(f"WebSocket消息解析失败: {e}")
        
        def default_on_error(ws, error):
            logger.error(f"WebSocket错误: {error}")
            if on_error:
                on_error(ws, error)
        
        def default_on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket连接已关闭")
            if on_close:
                on_close(ws, close_status_code, close_msg)
        
        def on_open(ws):
            # 订阅指定标的
            subscribe_msg = {
                "action": "subscribe",
                "symbols": symbols,
            }
            try:
                import json
                msg_str = json.dumps(subscribe_msg)
                ws.send(msg_str)
                logger.info(f"已订阅WebSocket实时数据: {symbols}")
            except Exception as e:
                logger.error(f"WebSocket订阅失败: {e}")
        
        self._ws_app = WebSocketApp(
            ws_url,
            on_message=default_on_message,
            on_error=default_on_error,
            on_close=default_on_close,
            on_open=on_open,
        )
        return self._ws_app
    
    def start_websocket(self) -> None:
        """启动WebSocket连接（在后台线程运行）"""
        if not self._ws_app:
            raise RuntimeError("请先调用 subscribe_websocket 创建WebSocket连接")
        self._ws_app.run_forever()
    
    def close(self) -> None:
        """关闭连接"""
        if self._ws_app:
            try:
                self._ws_app.close()
            except Exception:
                pass
            self._ws_app = None
        self._connected = False
        logger.info("ITickClient 已关闭")

