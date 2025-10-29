"""
基础策略示例
演示如何使用Quant_Banana框架开发简单的交易策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.data_loader import DataLoader
from src.strategies.base_strategy import BaseStrategy

class SimpleMovingAverageStrategy(BaseStrategy):
    """
    简单移动平均策略示例
    """
    
    def __init__(self, short_window=20, long_window=50):
        self.short_window = short_window
        self.long_window = long_window
        super().__init__()
    
    def generate_signals(self, data):
        """
        生成交易信号
        """
        # 计算短期和长期移动平均线
        data['SMA_short'] = data['close'].rolling(window=self.short_window).mean()
        data['SMA_long'] = data['close'].rolling(window=self.long_window).mean()
        
        # 生成信号
        data['signal'] = 0
        data['signal'][self.short_window:] = np.where(
            data['SMA_short'][self.short_window:] > data['SMA_long'][self.short_window:], 1, 0
        )
        data['positions'] = data['signal'].diff()
        
        return data

def main():
    """
    主函数 - 运行策略示例
    """
    print("🍌 Quant_Banana - 基础策略示例")
    print("=" * 50)
    
    # 这里可以添加具体的策略运行逻辑
    print("策略运行逻辑将在后续版本中实现...")
    print("当前项目结构已初始化完成！")

if __name__ == "__main__":
    main()
