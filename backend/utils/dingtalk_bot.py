from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Optional

import requests


class DingTalkBot:
    def __init__(self, webhook: str, secret: str | None = None):
        self.webhook = webhook
        self.secret = secret

    def _sign(self) -> dict:
        if not self.secret:
            return {}
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}".encode("utf-8")
        hmac_code = hmac.new(self.secret.encode("utf-8"), string_to_sign, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return {"timestamp": timestamp, "sign": sign}

    def send_text(self, content: str) -> None:
        url = self.webhook
        params = self._sign()
        payload = {"msgtype": "text", "text": {"content": content}}
        requests.post(url, params=params, json=payload, timeout=10)

    def send_markdown(self, title: str, text_md: str) -> None:
        url = self.webhook
        params = self._sign()
        payload = {"msgtype": "markdown", "markdown": {"title": title, "text": text_md}}
        requests.post(url, params=params, json=payload, timeout=10)


