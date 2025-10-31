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
    fields = {"confidence": None, "stop_loss": None, "take_profit": None, "position": None, "direction": None}
    
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
        "direction": [
            r'\*\*操作方向\*\*[：:]\s*(buy|sell|hold|买入|卖出|持有)',  # Markdown格式
            r'操作方向[：:]\s*(buy|sell|hold|买入|卖出|持有)',  # 普通格式
            r'方向[：:]\s*(buy|sell|hold|买入|卖出|持有)',
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
    
    # 提取操作方向
    for pattern in patterns["direction"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                direction_str = match.group(1).lower()
                # 标准化方向
                if direction_str in ("buy", "买入"):
                    fields["direction"] = "buy"
                elif direction_str in ("sell", "卖出"):
                    fields["direction"] = "sell"
                elif direction_str in ("hold", "持有", "空仓"):
                    fields["direction"] = "hold"
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
    strategy_action = evt_data.get("strategy_action", "")
    ai = evt_data.get("ai", {})
    
    # 获取融合信号信息
    fused_signal = evt_data.get("fused_signal", {})
    strategy_signal = evt_data.get("strategy_signal", {})
    ai_signal = evt_data.get("ai_signal", {})
    direction_match = evt_data.get("direction_match", False)
    fusion_type = evt_data.get("fusion_type", "unknown")
    
    # 优先使用融合信号，如果没有则使用AI输出
    if fused_signal:
        direction = fused_signal.get("direction", "")
        confidence = fused_signal.get("confidence", 0)
        position_size = fused_signal.get("position_size", 0)
        stop_loss = fused_signal.get("stop_loss", 0)
        take_profit = fused_signal.get("take_profit", 0)
    else:
        normalized = _normalize_ai_output(ai)
        # 尝试从AI输出中提取方向
        ai_fields = _extract_fields_from_text(str(normalized.get("summary", "")))
        direction = ai_fields.get("direction") or strategy_action  # 优先使用AI方向，否则用策略动作
        confidence = normalized.get("confidence", 0)
        if confidence and isinstance(confidence, float) and confidence <= 1:
            confidence = confidence * 100
        position_size = normalized.get("position", 0)
        stop_loss = normalized.get("stop_loss", 0)
        take_profit = normalized.get("take_profit", 0)
    
    # 获取AI输出的摘要（用于显示决策依据）
    normalized = _normalize_ai_output(ai)
    summary = normalized.get('summary', '').strip()
    
    # 账户信息
    account = _safe_get(evt_data, "ai_input.account", None)
    if account is None:
        account = evt_data.get("account") or {}
    capital_value = None
    for key in ["power", "BuyingPower", "cash", "available_cash", "total_assets"]:
        val = account.get(key) if isinstance(account, dict) else None
        if val is not None:
            try:
                capital_value = float(val)
                if capital_value > 0:
                    break
            except (ValueError, TypeError):
                pass
    
    capital = f"{capital_value:,.2f}" if capital_value and capital_value > 0 else "-"
    
    # 格式化显示
    direction_str = direction.upper() if direction else "-"
    strategy_dir = strategy_signal.get("direction", "").upper() if strategy_signal else (strategy_action.upper() if strategy_action else "-")
    
    # AI方向：优先从ai_signal获取，如果没有则从AI输出提取
    if ai_signal:
        ai_dir = ai_signal.get("direction", "").upper()
    else:
        ai_fields = _extract_fields_from_text(str(normalized.get("summary", "")))
        ai_dir = ai_fields.get("direction", "").upper() if ai_fields.get("direction") else "-"
    
    # 融合类型中文映射
    fusion_type_map = {
        "agreed": "方向一致",
        "conflict_resolved": "冲突解决",
        "conservative_hold": "保守观望",
        "unknown": "未知"
    }
    fusion_type_str = fusion_type_map.get(fusion_type, fusion_type)
    
    # 组装Markdown
    summary_section = ""
    if summary:
        if summary.startswith("##"):
            summary_section = f"\n{summary}\n"
        else:
            summary_section = f"\n#### 决策依据\n{summary}\n"
    
    md = (
        f"### 信号融合决策\n"
        f"- 标的: {symbol}\n"
        f"- 策略方向: {strategy_dir}\n"
        f"- AI方向: {ai_dir}\n"
        f"- 方向一致: {'✅' if direction_match else '❌'}\n"
        f"- 融合类型: {fusion_type_str}\n"
        f"- **最终决策**: {direction_str}\n"
        f"- 账户资金/购买力: {capital}\n"
        f"- 融合置信度: {confidence:.1f}%\n"
        f"- 建议仓位: {position_size}股\n"
        f"- 止损: {stop_loss:.2f} | 止盈: {take_profit:.2f}"
        f"{summary_section}"
    )
    return md


