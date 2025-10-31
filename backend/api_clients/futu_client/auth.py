"""
Futu OpenD 连接配置读取
从 config/settings/base.yaml 读取 futu_opend 的 host/port。
若缺失则提供默认值。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class FutuOpenDConfig:
    host: str = "127.0.0.1"
    port: int = 11111


def load_futu_opend_config(config_path: Optional[str] = None) -> FutuOpenDConfig:
    base_path = config_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "settings", "base.yaml")
    try:
        with open(base_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        futu_cfg = data.get("futu_opend", {})
        host = futu_cfg.get("host", "127.0.0.1")
        port = int(futu_cfg.get("port", 11111))
        return FutuOpenDConfig(host=host, port=port)
    except Exception:
        return FutuOpenDConfig()


