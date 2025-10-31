from __future__ import annotations

import json
import re
from typing import Any, Dict


def _safe_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _extract_fields_from_text(text: str) -> Dict[str, Any]:
    """从文本中提取字段，支持多种格式（Markdown、普通文本、中文冒号）。"""
    fields = {"confidence": None, "stop_loss": None, "take_profit": None, "position": None}
    
    # 支持的格式模式（按优先级）
    patterns = {
        "position": [
            r'\*\*仓位权重\*\*[：:]\s*(\d+(?:\.\d+)?)%?',  # Markdown格式: **仓位权重**: 65%
            r'仓位权重[：:]\s*(\d+(?:\.\d+)?)%?',  # 普通格式: 仓位权重: 65% 或 仓位权重：65%
        ],
        "stop_loss": [
            r'\*\*止损价格\*\*[：:]\s*(\d+(?:\.\d+)?)',  # Markdown格式: **止损价格**: 645.0
            r'止损价格[：:]\s*(\d+(?:\.\d+)?)',  # 普通格式: 止损价格: 645.0
        ],
        "take_profit": [
            r'\*\*止盈目标\*\*[：:]\s*(\d+(?:\.\d+)?)',  # Markdown格式: **止盈目标**: 635.0
            r'止盈目标[：:]\s*(\d+(?:\.\d+)?)',  # 普通格式: 止盈目标: 635.0
        ],
        "confidence": [
            r'\*\*信心度\*\*[：:]\s*(\d+(?:\.\d+)?)%?',  # Markdown格式: **信心度**: 78%
            r'信心度[：:]\s*(\d+(?:\.\d+)?)%?',  # 普通格式: 信心度: 78%
        ],
    }
    
    # 提取仓位权重
    for pattern in patterns["position"]:
        match = re.search(pattern, text)
        if match:
            try:
                fields["position"] = match.group(1)
                break
            except (ValueError, TypeError, IndexError):
                pass
    
    # 提取止损价格
    for pattern in patterns["stop_loss"]:
        match = re.search(pattern, text)
        if match:
            try:
                fields["stop_loss"] = float(match.group(1))
                break
            except (ValueError, TypeError, IndexError):
                pass
    
    # 提取止盈目标
    for pattern in patterns["take_profit"]:
        match = re.search(pattern, text)
        if match:
            try:
                fields["take_profit"] = float(match.group(1))
                break
            except (ValueError, TypeError, IndexError):
                pass
    
    # 提取信心度
    for pattern in patterns["confidence"]:
        match = re.search(pattern, text)
        if match:
            try:
                conf_val = float(match.group(1))
                fields["confidence"] = conf_val / 100.0 if conf_val > 1 else conf_val
                break
            except (ValueError, TypeError, IndexError):
                pass
    
    return fields


def _normalize_ai_output(ai: Dict[str, Any]) -> Dict[str, Any]:
    """从AI返回中提炼用于展示的字段，避免原始JSON直出。"""
    out = ai.get("output")
    result: Dict[str, Any] = {"summary": "", "confidence": None, "stop_loss": None, "take_profit": None, "position": None}
    
    # 获取summary文本
    summary_text = ""
    if isinstance(out, dict):
        # 结构化：优先 summary，其次字段
        summary_text = str(out.get("summary") or out.get("text") or "")
        result["confidence"] = out.get("confidence")
        # 兼容不同命名
        result["stop_loss"] = out.get("stop_loss") or out.get("sl")
        result["take_profit"] = out.get("take_profit") or out.get("tp")
        result["position"] = out.get("position") or out.get("position_weight") or out.get("size")
    elif isinstance(out, str):
        # 文本：去掉围栏/多余转义
        summary_text = out.strip()
        summary_text = re.sub(r"```[\s\S]*?```", "", summary_text)  # 移除代码围栏块
        summary_text = summary_text.replace("\\n", "\n")
    else:
        # 兜底：尽量不输出JSON
        try:
            summary_text = json.dumps(out, ensure_ascii=False)
        except Exception:
            summary_text = str(out)
    
    # 先从原始文本中提取字段（在清理前提取，确保能正确提取）
    original_text = summary_text.strip()
    if original_text and ("决策详情" in original_text or "仓位权重" in original_text or "止损价格" in original_text):
        extracted = _extract_fields_from_text(original_text)
        # 只有在字段还未设置时才使用提取的值
        if not result.get("position") and extracted.get("position"):
            result["position"] = extracted["position"]
        if not result.get("stop_loss") and extracted.get("stop_loss") is not None:
            result["stop_loss"] = extracted["stop_loss"]
        if not result.get("take_profit") and extracted.get("take_profit") is not None:
            result["take_profit"] = extracted["take_profit"]
        if not result.get("confidence") and extracted.get("confidence") is not None:
            result["confidence"] = extracted["confidence"]
    
    # 清理文本：移除"最终决策"和"决策详情"部分，只保留"决策依据"
    summary_text = summary_text.strip()
    # 移除 "## 最终决策" 及其后的内容，直到 "## 决策详情" 或 "## 决策依据"
    summary_text = re.sub(r'##\s*最终决策[\s\S]*?(?=##\s*决策详情|##\s*决策依据|$)', '', summary_text, flags=re.IGNORECASE)
    # 移除 "## 决策详情" 及其后的内容，直到 "## 决策依据"
    summary_text = re.sub(r'##\s*决策详情[\s\S]*?(?=##\s*决策依据|$)', '', summary_text, flags=re.IGNORECASE)
    # 清理多余的空白和换行
    summary_text = summary_text.strip()
    # 如果没有保留任何内容（或者只保留了空白），则summary为空
    if not summary_text or (not summary_text.startswith("##") and "决策依据" not in summary_text):
        summary_text = ""
    
    # 限制长度
    if summary_text:
        result["summary"] = summary_text[:800] if len(summary_text) > 800 else summary_text
    else:
        result["summary"] = ""
    
    return result


def format_ai_decision(evt_data: Dict[str, Any]) -> str:
    symbol = evt_data.get("symbol")
    action = evt_data.get("strategy_action")
    ai = evt_data.get("ai", {})
    normalized = _normalize_ai_output(ai)
    
    # 更健壮的账户信息读取
    account = _safe_get(evt_data, "ai_input.account", None)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[格式化] 从 ai_input.account 读取: {account}")
    if account is None:
        # 尝试直接从顶层获取
        account = evt_data.get("account") or {}
        logger.info(f"[格式化] 从顶层 account 读取: {account}")
    if not isinstance(account, dict):
        logger.warning(f"[格式化] account 不是字典: {type(account)}, 值: {account}")
        account = {}
    
    # 尝试多种字段名
    capital_value = None
    for key in ["power", "BuyingPower", "cash", "available_cash", "total_assets"]:
        val = account.get(key)
        if val is not None:
            try:
                capital_value = float(val)
                if capital_value > 0:
                    break
            except (ValueError, TypeError):
                pass
    
    # 格式化资金显示（添加千位分隔符）
    if capital_value is not None and capital_value > 0:
        capital = f"{capital_value:,.2f}"
        # 如果有购买力和现金，都显示
        power = account.get("power") or account.get("BuyingPower")
        cash = account.get("cash") or account.get("available_cash")
        if power is not None and cash is not None:
            try:
                power_val = float(power)
                cash_val = float(cash)
                if power_val != cash_val:
                    capital = f"购买力: {power_val:,.2f} | 现金: {cash_val:,.2f}"
            except (ValueError, TypeError):
                capital = f"{capital_value:,.2f}"
    else:
        capital = "-"

    conf = normalized.get("confidence")
    sl = normalized.get("stop_loss")
    tp = normalized.get("take_profit")
    pos = normalized.get("position")
    
    # 格式化置信度
    conf_str = "-"
    if conf is not None:
        try:
            if isinstance(conf, (float, int)):
                if 0 <= conf <= 1:
                    conf_str = f"{int(conf*100)}%"
                else:
                    conf_str = f"{int(conf)}%"
        except (ValueError, TypeError):
            pass
    
    # 格式化仓位
    pos_str = "-"
    if pos is not None:
        try:
            pos_val = float(pos) if isinstance(pos, str) else pos
            pos_str = f"{pos_val}%"
        except (ValueError, TypeError):
            pos_str = str(pos)
    
    # 格式化止损
    sl_str = "-"
    if sl is not None:
        try:
            sl_val = float(sl) if isinstance(sl, str) else sl
            sl_str = f"{sl_val:.2f}"
        except (ValueError, TypeError):
            sl_str = str(sl)
    
    # 格式化止盈
    tp_str = "-"
    if tp is not None:
        try:
            tp_val = float(tp) if isinstance(tp, str) else tp
            tp_str = f"{tp_val:.2f}"
        except (ValueError, TypeError):
            tp_str = str(tp)

    # 组装精简Markdown
    summary = normalized.get('summary', '').strip()
    # 如果摘要为空，则不显示摘要部分
    summary_section = ""
    if summary:
        # 如果摘要已经包含标题，直接使用；否则添加标题
        if summary.startswith("##"):
            summary_section = f"\n{summary}\n"
        else:
            summary_section = f"\n#### 决策依据\n{summary}\n"
    
    md = (
        f"### AI 决策\n"
        f"- 标的: {symbol}\n"
        f"- 动作: {action}\n"
        f"- 账户资金/购买力: {capital}\n"
        f"- 置信度: {conf_str}\n"
        f"- 建议仓位: {pos_str}\n"
        f"- 止损: {sl_str} | 止盈: {tp_str}"
        f"{summary_section}"
    )
    return md


