"""
信号融合引擎 - 负责整合策略机和AI信号
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging
import json
import os


class SignalSource(Enum):
    """信号来源"""
    STRATEGY_ENGINE = "strategy_engine"
    AI_DECISION = "ai_decision"


class SignalDirection(Enum):
    """信号方向"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    
    @classmethod
    def from_str(cls, action: str) -> SignalDirection:
        """从字符串转换为SignalDirection"""
        action_upper = str(action).upper()
        if action_upper in ("BUY", "买入", "BUY"):
            return cls.BUY
        elif action_upper in ("SELL", "卖出", "SELL"):
            return cls.SELL
        elif action_upper in ("HOLD", "持有", "空仓", "HOLD"):
            return cls.HOLD
        else:
            # 默认HOLD
            return cls.HOLD


@dataclass
class TradingSignal:
    """交易信号数据类"""
    source: SignalSource
    direction: SignalDirection
    symbol: str
    timestamp: datetime
    confidence: float  # 0-100
    price: float
    position_size: int
    stop_loss: float
    take_profit: float
    reason: str
    metadata: Dict  # 额外元数据
    
    def __post_init__(self):
        self.weighted_score = self.calculate_weighted_score()
    
    def calculate_weighted_score(self) -> float:
        """计算信号的加权得分"""
        base_score = self.confidence
        
        # 根据信号源调整基础权重
        if self.source == SignalSource.AI_DECISION:
            base_score *= 1.1  # AI信号略微加权
        
        # 风险收益比调整（需要有效的止损和止盈）
        if self.stop_loss > 0 and self.take_profit > 0 and abs(self.price - self.stop_loss) > 0:
            try:
                risk_reward = abs(self.take_profit - self.price) / abs(self.price - self.stop_loss)
                if risk_reward >= 2.0:
                    base_score *= 1.2
                elif risk_reward >= 1.5:
                    base_score *= 1.1
            except (ZeroDivisionError, ValueError):
                pass
        
        return min(100, base_score)


class SignalFusionEngine:
    """
    信号融合引擎 - 负责整合策略机和AI信号
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化融合引擎
        
        Args:
            config: 配置字典，包含source_weights等
        """
        self.signal_history: List[TradingSignal] = []
        
        cfg = config or {}
        # 初始权重配置
        source_weights_cfg = cfg.get("source_weights", {})
        self.source_weights = {
            SignalSource.STRATEGY_ENGINE: float(source_weights_cfg.get("strategy", 0.45)),
            SignalSource.AI_DECISION: float(source_weights_cfg.get("ai", 0.55))
        }
        
        # 动态权重调整参数
        self.performance_tracking = {
            SignalSource.STRATEGY_ENGINE: {'success': 0, 'total': 0, 'recent_performance': 0.5},
            SignalSource.AI_DECISION: {'success': 0, 'total': 0, 'recent_performance': 0.5}
        }
        
        # 性能数据持久化路径
        self.performance_file = cfg.get("performance_file", "data/signal_performance.json")
        self._load_performance_data()
        
        self.logger = logging.getLogger(__name__)
    
    def _load_performance_data(self):
        """从文件加载性能数据"""
        if os.path.exists(self.performance_file):
            try:
                with open(self.performance_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for source_str, perf in data.items():
                        try:
                            source = SignalSource(source_str)
                            self.performance_tracking[source] = perf
                        except ValueError:
                            pass
            except Exception as e:
                logging.getLogger(__name__).warning(f"加载性能数据失败: {e}")
    
    def _save_performance_data(self):
        """保存性能数据到文件"""
        try:
            os.makedirs(os.path.dirname(self.performance_file), exist_ok=True)
            data = {
                source.value: perf for source, perf in self.performance_tracking.items()
            }
            with open(self.performance_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.getLogger(__name__).warning(f"保存性能数据失败: {e}")
    
    def update_source_weights(self):
        """基于历史表现动态调整信号源权重"""
        strat_perf = self.performance_tracking[SignalSource.STRATEGY_ENGINE]['recent_performance']
        ai_perf = self.performance_tracking[SignalSource.AI_DECISION]['recent_performance']
        
        total_perf = strat_perf + ai_perf
        if total_perf > 0:
            self.source_weights[SignalSource.STRATEGY_ENGINE] = strat_perf / total_perf * 0.9
            self.source_weights[SignalSource.AI_DECISION] = ai_perf / total_perf * 0.9
        
        self.logger.info(f"更新权重: 策略机={self.source_weights[SignalSource.STRATEGY_ENGINE]:.2f}, "
                        f"AI={self.source_weights[SignalSource.AI_DECISION]:.2f}")
        self._save_performance_data()
    
    def record_trade_outcome(self, signal: TradingSignal, success: bool, pnl: float):
        """记录交易结果用于性能跟踪"""
        source = signal.source
        self.performance_tracking[source]['total'] += 1
        
        if success:
            self.performance_tracking[source]['success'] += 1
        
        # 计算近期表现（最近50次交易）
        recent_trades = [s for s in self.signal_history[-50:] if s.source == source]
        if recent_trades:
            success_rate = len([t for t in recent_trades if getattr(t, 'success', False)]) / len(recent_trades)
            self.performance_tracking[source]['recent_performance'] = success_rate
        
        # 标记信号的成功状态
        signal.success = success
        signal.pnl = pnl
        
        self._save_performance_data()
    
    def fuse_signals(self, strategy_signal: TradingSignal, ai_signal: TradingSignal) -> TradingSignal:
        """
        融合策略机和AI信号，生成最优信号
        
        Args:
            strategy_signal: 策略信号
            ai_signal: AI信号
            
        Returns:
            融合后的信号
        """
        # 1. 方向一致性检查
        direction_agreement = strategy_signal.direction == ai_signal.direction
        
        if direction_agreement:
            # 方向一致 - 增强信号
            fused_signal = self._fuse_agreed_signals(strategy_signal, ai_signal)
        else:
            # 方向不一致 - 冲突解决
            fused_signal = self._resolve_conflicting_signals(strategy_signal, ai_signal)
        
        self.signal_history.append(fused_signal)
        
        # 限制历史记录大小（保留最近1000条）
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]
        
        return fused_signal
    
    def _fuse_agreed_signals(self, strat_signal: TradingSignal, ai_signal: TradingSignal) -> TradingSignal:
        """融合方向一致的信号"""
        # 加权平均计算关键参数
        strat_weight = self.source_weights[SignalSource.STRATEGY_ENGINE]
        ai_weight = self.source_weights[SignalSource.AI_DECISION]
        
        fused_confidence = (strat_signal.confidence * strat_weight + 
                          ai_signal.confidence * ai_weight)
        
        # 选择更保守的仓位和风控参数
        fused_position = min(strat_signal.position_size, ai_signal.position_size)
        fused_stop_loss = self._calculate_fused_stop_loss(strat_signal, ai_signal)
        fused_take_profit = self._calculate_fused_take_profit(strat_signal, ai_signal)
        
        return TradingSignal(
            source=SignalSource.AI_DECISION,  # 标记为融合信号
            direction=strat_signal.direction,  # 方向一致
            symbol=strat_signal.symbol,
            timestamp=datetime.now(),
            confidence=fused_confidence,
            price=(strat_signal.price + ai_signal.price) / 2,
            position_size=fused_position,
            stop_loss=fused_stop_loss,
            take_profit=fused_take_profit,
            reason=f"信号融合: 策略机({strat_signal.confidence:.1f}%) + AI({ai_signal.confidence:.1f}%) 方向一致",
            metadata={
                'fusion_type': 'agreed',
                'original_sources': [strat_signal.source.value, ai_signal.source.value],
                'component_confidences': [strat_signal.confidence, ai_signal.confidence]
            }
        )
    
    def _resolve_conflicting_signals(self, strat_signal: TradingSignal, ai_signal: TradingSignal) -> TradingSignal:
        """解决方向冲突的信号"""
        strat_score = strat_signal.weighted_score * self.source_weights[SignalSource.STRATEGY_ENGINE]
        ai_score = ai_signal.weighted_score * self.source_weights[SignalSource.AI_DECISION]
        
        self.logger.info(f"信号冲突: 策略机({strat_score:.1f}) vs AI({ai_score:.1f})")
        
        if abs(strat_score - ai_score) <= 10:  # 分数接近时
            # 选择更保守的方向或保持观望
            return self._conservative_conflict_resolution(strat_signal, ai_signal)
        else:
            # 选择分数更高的信号
            winning_signal = strat_signal if strat_score > ai_score else ai_signal
            
            # 但降低置信度以反映冲突
            adjusted_confidence = winning_signal.confidence * 0.7
            
            return TradingSignal(
                source=winning_signal.source,
                direction=winning_signal.direction,
                symbol=winning_signal.symbol,
                timestamp=datetime.now(),
                confidence=adjusted_confidence,
                price=winning_signal.price,
                position_size=int(winning_signal.position_size * 0.7),  # 降低仓位
                stop_loss=winning_signal.stop_loss,
                take_profit=winning_signal.take_profit,
                reason=f"冲突解决: {winning_signal.source.value}胜出 (原置信度:{winning_signal.confidence:.1f}%)",
                metadata={
                    'fusion_type': 'conflict_resolved',
                    'winning_source': winning_signal.source.value,
                    'original_scores': [strat_score, ai_score],
                    'confidence_reduction': 0.3,
                    'conflicting_directions': [strat_signal.direction.value, ai_signal.direction.value]
                }
            )
    
    def _conservative_conflict_resolution(self, strat_signal: TradingSignal, ai_signal: TradingSignal) -> TradingSignal:
        """保守的冲突解决策略"""
        # 在严重冲突时选择观望
        return TradingSignal(
            source=SignalSource.AI_DECISION,
            direction=SignalDirection.HOLD,  # 选择观望
            symbol=strat_signal.symbol,
            timestamp=datetime.now(),
            confidence=40,  # 低置信度
            price=(strat_signal.price + ai_signal.price) / 2,
            position_size=0,  # 无仓位
            stop_loss=0,
            take_profit=0,
            reason="严重信号冲突，建议观望",
            metadata={
                'fusion_type': 'conservative_hold',
                'conflicting_directions': [strat_signal.direction.value, ai_signal.direction.value],
                'component_confidences': [strat_signal.confidence, ai_signal.confidence]
            }
        )
    
    def _calculate_fused_stop_loss(self, strat_signal: TradingSignal, ai_signal: TradingSignal) -> float:
        """计算融合止损位 - 选择更保守的止损"""
        # 确保两个信号都有有效的止损
        if strat_signal.stop_loss <= 0 or ai_signal.stop_loss <= 0:
            return max(strat_signal.stop_loss, ai_signal.stop_loss)
        
        if strat_signal.direction == SignalDirection.BUY:
            return min(strat_signal.stop_loss, ai_signal.stop_loss)  # 取更低的止损（更保守）
        else:
            return max(strat_signal.stop_loss, ai_signal.stop_loss)  # 取更高的止损（更保守）
    
    def _calculate_fused_take_profit(self, strat_signal: TradingSignal, ai_signal: TradingSignal) -> float:
        """计算融合止盈位 - 选择更保守的止盈"""
        # 确保两个信号都有有效的止盈
        if strat_signal.take_profit <= 0 or ai_signal.take_profit <= 0:
            return max(strat_signal.take_profit, ai_signal.take_profit)
        
        if strat_signal.direction == SignalDirection.BUY:
            return min(strat_signal.take_profit, ai_signal.take_profit)  # 取更低的止盈（更保守）
        else:
            return max(strat_signal.take_profit, ai_signal.take_profit)  # 取更高的止盈（更保守）


class SignalFilter:
    """信号质量过滤器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化过滤器
        
        Args:
            config: 配置字典，包含min_confidence等阈值
        """
        cfg = config or {}
        self.min_confidence = float(cfg.get("min_confidence", 60))
        self.min_risk_reward = float(cfg.get("min_risk_reward", 1.3))
        self.max_position_ratio = float(cfg.get("max_position_ratio", 0.3))
        self.cooldown_period_minutes = int(cfg.get("cooldown_period_minutes", 10))
        
        self.last_signal_time: Dict[str, datetime] = {}
        self.current_capital = float(cfg.get("initial_capital", 10000))
        
        self.logger = logging.getLogger(__name__)
    
    def update_capital(self, capital: float):
        """更新当前资金"""
        self.current_capital = capital
    
    def should_accept_signal(self, signal: TradingSignal) -> tuple[bool, str]:
        """
        信号质量过滤
        
        Returns:
            (是否接受, 拒绝原因)
        """
        # 置信度过滤
        if signal.confidence < self.min_confidence:
            return False, f"置信度过低: {signal.confidence:.1f}% < {self.min_confidence}%"
        
        # 如果是HOLD，直接接受（不执行交易）
        if signal.direction == SignalDirection.HOLD:
            return True, "HOLD信号"
        
        # 风险收益比过滤（需要有效的止损和止盈）
        if signal.stop_loss > 0 and signal.take_profit > 0 and abs(signal.price - signal.stop_loss) > 0:
            try:
                risk_reward = abs(signal.take_profit - signal.price) / abs(signal.price - signal.stop_loss)
                if risk_reward < self.min_risk_reward:
                    return False, f"风险收益比不足: {risk_reward:.2f} < {self.min_risk_reward}"
            except (ZeroDivisionError, ValueError):
                pass
        
        # 仓位大小过滤
        position_value = signal.price * signal.position_size
        max_position_value = self.current_capital * self.max_position_ratio
        if position_value > max_position_value:
            return False, f"仓位过大: {position_value:.0f} > {max_position_value:.0f}"
        
        # 冷却期过滤
        key = f"{signal.symbol}_{signal.direction.value}"
        if key in self.last_signal_time:
            time_diff = datetime.now() - self.last_signal_time[key]
            cooldown_delta = timedelta(minutes=self.cooldown_period_minutes)
            if time_diff < cooldown_delta:
                remaining = (cooldown_delta - time_diff).total_seconds() / 60
                return False, f"冷却期内: {remaining:.1f}分钟剩余"
        
        self.last_signal_time[key] = datetime.now()
        
        # 清理过期记录（保留最近1000条）
        if len(self.last_signal_time) > 1000:
            expired_keys = [k for k, v in self.last_signal_time.items() 
                          if datetime.now() - v > timedelta(hours=24)]
            for k in expired_keys:
                del self.last_signal_time[k]
        
        return True, "信号有效"

