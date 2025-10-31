from __future__ import annotations

"""
Futu OpenD 客户端封装：
- 连接 OpenD（行情）
- 拉取历史 K 线
- 预留订阅/回调（后续接入 futu SDK 的 push）
"""

import logging
from typing import List, Optional, Tuple

from datetime import datetime

logger = logging.getLogger(__name__)


class FutuClient:
    def __init__(self, host: str, api_port: int, ws_port: int, ws_key: str):
        self.host = host
        self.api_port = api_port
        self.ws_port = ws_port
        self.ws_key = ws_key
        self._quote_ctx = None  # 占位：futu.OpenQuoteContext

    def connect(self) -> None:
        if self._quote_ctx is not None:
            return
        try:
            from futu import OpenQuoteContext  # type: ignore
            self._quote_ctx = OpenQuoteContext(host=self.host, port=self.api_port)
            logger.info("FutuClient 已连接 OpenQuoteContext")
        except Exception as e:
            logger.error(f"连接 Futu OpenD 失败: {e}\n")
            raise

    def subscribe_kl(self, symbols: list[str], kl_type: str) -> None:
        if self._quote_ctx is None:
            raise RuntimeError("FutuClient 未连接")
        from futu import SubType, KLType  # type: ignore

        kl_map = {
            "K_1M": (KLType.K_1M, SubType.K_1M),
            "K_3M": (KLType.K_3M, SubType.K_3M),
            "K_5M": (KLType.K_5M, SubType.K_5M),
            "K_15M": (KLType.K_15M, SubType.K_15M),
            "K_30M": (KLType.K_30M, SubType.K_30M),
            "K_60M": (KLType.K_60M, SubType.K_60M),
            "K_DAY": (KLType.K_DAY, SubType.K_DAY),
        }
        pair = kl_map.get(kl_type)
        if pair is None:
            raise ValueError(f"不支持的K线类型: {kl_type}")
        _klt, sub = pair
        ret, msg = self._quote_ctx.subscribe(symbols, [sub], subscribe_push=False)
        if ret != 0:
            raise RuntimeError(f"订阅KL失败: {msg}")

    def get_recent_kline(
        self, symbol: str, ktype: str, count: int
    ) -> List[Tuple[datetime, float, float, float, float, float]]:
        """使用 futu SDK 获取最近K线数据。ktype 示例: 'K_1M','K_5M','K_DAY'"""
        if self._quote_ctx is None:
            raise RuntimeError("FutuClient 未连接")
        from futu import KLType  # type: ignore

        kl_map = {
            "K_1M": KLType.K_1M,
            "K_3M": KLType.K_3M,
            "K_5M": KLType.K_5M,
            "K_15M": KLType.K_15M,
            "K_30M": KLType.K_30M,
            "K_60M": KLType.K_60M,
            "K_DAY": KLType.K_DAY,
        }
        kl_type = kl_map.get(ktype)
        if kl_type is None:
            raise ValueError(f"不支持的K线类型: {ktype}")

        ret, df = self._quote_ctx.get_cur_kline(symbol, count, kl_type)
        if ret != 0:
            raise RuntimeError(f"获取K线失败: {df}")
        rows: List[Tuple[datetime, float, float, float, float, float]] = []
        for _, r in df.iterrows():
            ts = datetime.strptime(str(r["time_key"]), "%Y-%m-%d %H:%M:%S")
            rows.append(
                (
                    ts,
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    float(r["volume"]),
                )
            )
        return rows

    def get_account_info(self, env: str = "SIMULATE") -> dict:
        """尽力获取账户信息（现金、购买力、持仓）。若未登录或无权限，返回错误信息。
        
        Args:
            env: "SIMULATE" 或 "REAL"，默认 SIMULATE
        """
        info: dict = {"ok": False}
        try:
            from futu import TrdEnv  # type: ignore
            env_enum = TrdEnv.SIMULATE if env.upper() == "SIMULATE" else TrdEnv.REAL
            
            # 优先尝试港股交易上下文
            from futu import OpenHKTradeContext  # type: ignore

            with OpenHKTradeContext(host=self.host, port=self.api_port) as trd:
                # get_acc_list 不接受 env 参数，需要先获取所有账户，然后筛选
                ret, acc = trd.get_acc_list()
                logger.info(f"[账户信息] get_acc_list 返回: ret={ret}, acc={acc}")
                if ret != 0:
                    raise RuntimeError(f"get_acc_list 失败: {acc}")
                if acc.empty:
                    raise RuntimeError("账户列表为空")
                
                # 直接取第一个账户（环境通过 trd_env 参数在后续 API 调用中指定）
                acc_id = acc.iloc[0]["acc_id"]
                logger.info(f"[账户信息] 账户列表: {acc.to_dict('records')}")
                    
                logger.info(f"[账户信息] 账户ID: {acc_id}, 环境: {env}")
                snapshot = {"account": str(acc_id), "env": env}
                
                try:
                    # 使用 accinfo_query 查询账户信息（资金、持仓等）
                    r1, funds = trd.accinfo_query(trd_env=env_enum, acc_id=acc_id)
                    logger.info(f"[账户信息] accinfo_query 返回: ret={r1}, funds={funds}")
                    if r1 == 0 and not funds.empty:
                        row = funds.iloc[0]
                        logger.info(f"[账户信息] 原始 funds 行: {row.to_dict()}")
                        # 尝试多种可能的字段名
                        cash_val = 0.0
                        power_val = 0.0
                        # 现金字段：cash, available_cash, total_assets, Cash
                        for cash_key in ["cash", "available_cash", "total_assets", "Cash", "AvailableCash"]:
                            if cash_key in row:
                                try:
                                    val = row[cash_key]
                                    if val is not None:
                                        cash_val = float(val)
                                        if cash_val > 0:
                                            break
                                except (ValueError, TypeError):
                                    pass
                        # 购买力字段：power, BuyingPower, buying_power, available_margin, MaxCashOut, TotalAssets
                        for power_key in ["power", "BuyingPower", "buying_power", "available_margin", "MaxCashOut", "TotalAssets"]:
                            if power_key in row:
                                try:
                                    val = row[power_key]
                                    if val is not None:
                                        power_val = float(val)
                                        if power_val > 0:
                                            break
                                except (ValueError, TypeError):
                                    pass
                        
                        # 如果购买力为0，使用现金作为购买力
                        if power_val == 0 and cash_val > 0:
                            power_val = cash_val
                            
                        snapshot.update(
                            {
                                "cash": cash_val,
                                "power": power_val,
                            }
                        )
                        logger.info(f"[账户信息] 提取成功: cash={cash_val}, power={power_val}")
                    else:
                        logger.warning(f"[账户信息] accinfo_query 失败或为空: ret={r1}, funds={funds}")
                except Exception as e:
                    logger.error(f"[账户信息] accinfo_query 异常: {e}", exc_info=True)
                    pass
                try:
                    # 使用 position_list_query 查询持仓
                    r2, pos = trd.position_list_query(trd_env=env_enum, acc_id=acc_id)
                    logger.info(f"[账户信息] position_list_query 返回: ret={r2}")
                    if r2 == 0:
                        positions = []
                        if not pos.empty:
                            for _, p in pos.iterrows():
                                positions.append(
                                    {
                                        "symbol": str(p.get("code", "")),
                                        "qty": float(p.get("qty", 0) or 0),
                                        "cost_price": float(p.get("cost_price", 0) or 0),
                                    }
                                )
                        snapshot["positions"] = positions
                        logger.info(f"[账户信息] 持仓数量: {len(positions)}")
                except Exception as e:
                    logger.error(f"[账户信息] position_list_query 异常: {e}", exc_info=True)
                    pass
                snapshot["ok"] = True
                logger.info(f"[账户信息] 最终返回: {snapshot}")
                return snapshot
        except Exception as e:
            logger.error(f"[账户信息] 获取账户信息失败: {e}", exc_info=True)
            info["error"] = str(e)
        return info

    def place_order(self, symbol: str, side: str, qty: int, price: float | None = None, order_type: str = "MARKET", acc_id: str | None = None, env: str = "SIMULATE") -> dict:
        """下单：side='BUY'/'SELL', order_type='MARKET'/'LIMIT', env='SIMULATE'/'REAL'"""
        from futu import TrdEnv, TrdSide, OrderType  # type: ignore
        env_enum = TrdEnv.SIMULATE if env.upper() == "SIMULATE" else TrdEnv.REAL
        side_enum = TrdSide.BUY if side.upper() == "BUY" else TrdSide.SELL
        order_type_enum = OrderType.MARKET if order_type.upper() == "MARKET" else OrderType.NORMAL
        # 选择交易上下文：港股或美股
        is_hk = symbol.startswith("HK.")
        ctx_class = None
        if is_hk:
            from futu import OpenHKTradeContext  # type: ignore
            ctx_class = OpenHKTradeContext
        else:
            from futu import OpenUSTradeContext  # type: ignore
            ctx_class = OpenUSTradeContext
        result: dict = {"ok": False}
        try:
            with ctx_class(host=self.host, port=self.api_port) as trd:
                # 获取账户列表（get_acc_list 不接受 env 参数）
                ret, acc_df = trd.get_acc_list()
                if ret != 0 or acc_df.empty:
                    result["error"] = f"获取账户失败: {acc_df}"
                    logger.error(f"[下单] 获取账户失败: {ret}, {acc_df}")
                    return result
                # 选择账户：优先 acc_id，否则取第一个
                # 确保账户ID是整数类型（Futu SDK需要）
                if acc_id:
                    try:
                        target_acc = int(acc_id)
                    except (ValueError, TypeError):
                        target_acc = int(acc_df.iloc[0]["acc_id"])
                else:
                    target_acc = int(acc_df.iloc[0]["acc_id"])
                logger.info(f"[下单] 使用账户: {target_acc} (类型: {type(target_acc)}), 环境: {env}")
                # 下单
                if order_type_enum == OrderType.MARKET:
                    ret, data = trd.place_order(price=None, qty=float(qty), code=symbol, trd_side=side_enum, order_type=order_type_enum, trd_env=env_enum, acc_id=target_acc)
                else:
                    if price is None:
                        result["error"] = "限价单必须指定价格"
                        return result
                    ret, data = trd.place_order(price=float(price), qty=float(qty), code=symbol, trd_side=side_enum, order_type=order_type_enum, trd_env=env_enum, acc_id=target_acc)
                if ret != 0:
                    result["error"] = str(data)
                    logger.error(f"[下单] 失败: {ret}, {data}")
                    return result
                # 解析返回
                order_id = str(data.get("order_id", "")) if isinstance(data, dict) else (str(data.iloc[0]["order_id"]) if not data.empty else "")
                result["ok"] = True
                result["order_id"] = order_id
                result["raw"] = data
                logger.info(f"[下单] 成功: {symbol} {side} {qty} @ {price or '市价'}, order_id={order_id}")
                return result
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"[下单] 异常: {e}", exc_info=True)
        return result

    def close(self) -> None:
        try:
            if self._quote_ctx is not None:
                # self._quote_ctx.close()
                self._quote_ctx = None
        finally:
            logger.info("FutuClient 已关闭")


