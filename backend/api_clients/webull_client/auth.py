"""
Webull API认证模块
"""

import requests
import hashlib
import time
import json
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class WebullAuth:
    """Webull认证类"""
    
    def __init__(self, username: str, password: str, device_id: str):
        self.username = username
        self.password = password
        self.device_id = device_id
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        self.base_url = "https://quotes-gw.webull.com"
    
    def _generate_signature(self, params: Dict) -> str:
        """生成签名"""
        # Webull API签名逻辑
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])
        return hashlib.md5(query_string.encode()).hexdigest()
    
    def login(self) -> bool:
        """登录获取访问令牌"""
        try:
            # 第一步：获取验证码
            verify_url = f"{self.base_url}/api/user/verification/send"
            verify_params = {
                "account": self.username,
                "accountType": 2,  # 邮箱登录
                "deviceId": self.device_id,
                "regionId": 1,  # 美国
                "t": int(time.time() * 1000)
            }
            
            response = requests.post(verify_url, json=verify_params)
            if response.status_code != 200:
                logger.error(f"获取验证码失败: {response.text}")
                return False
            
            # 第二步：验证码登录
            login_url = f"{self.base_url}/api/user/login"
            login_params = {
                "account": self.username,
                "pwd": self.password,
                "deviceId": self.device_id,
                "regionId": 1,
                "t": int(time.time() * 1000)
            }
            
            response = requests.post(login_url, json=login_params)
            if response.status_code != 200:
                logger.error(f"登录失败: {response.text}")
                return False
            
            data = response.json()
            if data.get("success"):
                self.access_token = data.get("accessToken")
                self.refresh_token = data.get("refreshToken")
                self.token_expires_at = time.time() + 3600  # 1小时过期
                logger.info("Webull登录成功")
                return True
            else:
                logger.error(f"登录失败: {data.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"登录过程中出错: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """刷新访问令牌"""
        if not self.refresh_token:
            logger.warning("没有刷新令牌，需要重新登录")
            return self.login()
        
        try:
            refresh_url = f"{self.base_url}/api/user/refreshToken"
            refresh_params = {
                "refreshToken": self.refresh_token,
                "deviceId": self.device_id,
                "regionId": 1
            }
            
            response = requests.post(refresh_url, json=refresh_params)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.access_token = data.get("accessToken")
                    self.token_expires_at = time.time() + 3600
                    logger.info("令牌刷新成功")
                    return True
            
            logger.warning("令牌刷新失败，尝试重新登录")
            return self.login()
            
        except Exception as e:
            logger.error(f"刷新令牌时出错: {e}")
            return False
    
    def is_token_valid(self) -> bool:
        """检查令牌是否有效"""
        if not self.access_token:
            return False
        
        if self.token_expires_at and time.time() >= self.token_expires_at:
            return False
        
        return True
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        if not self.is_token_valid():
            if not self.refresh_access_token():
                raise Exception("无法获取有效的访问令牌")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
