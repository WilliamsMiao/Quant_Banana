<template>
  <div class="alpha-arena">
    <NavBar />
    
    <main class="main-content">
      <div class="container">
        <!-- 股票价格 -->
        <CryptoPrices />
        
        <!-- 模型排行榜 -->
        <ModelLeaderboard />
        
        <!-- 账户价值图表 -->
        <AccountChart />
        
        <!-- AI策略卡片网格 -->
        <div class="models-section">
          <div class="models-grid">
            <ModelCard 
              v-for="model in models" 
              :key="model.id"
              :model="model"
              @click="selectModel"
            />
          </div>
        </div>
        
        <!-- 选项卡区域 -->
        <div class="tabs-section">
          <div class="tabs">
            <button 
              v-for="tab in tabs" 
              :key="tab.id"
              :class="['tab', { active: activeTab === tab.id }]"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </div>
          
          <div class="tab-content">
            <div v-if="activeTab === 'trades'" class="tab-panel">
              <h3>Completed Trades</h3>
              <p>股票交易历史数据将在此显示，包括买入、卖出订单的详细信息</p>
            </div>
            
            <div v-if="activeTab === 'chat'" class="tab-panel">
              <h3>Strategy Chat</h3>
              <p>AI策略对话内容将在此显示，包括策略决策过程和交易信号分析</p>
            </div>
            
            <div v-if="activeTab === 'positions'" class="tab-panel">
              <h3>Stock Positions</h3>
              <p>股票持仓信息将在此显示，包括当前持有的股票数量和市值</p>
            </div>
            
            <div v-if="activeTab === 'readme'" class="tab-panel">
              <div class="readme-content">
                <h3>AI股票交易竞技场</h3>
                <p>
                  Alpha Arena 是第一个专门测试AI股票投资能力的基准测试平台。每个AI模型都获得10,000美元的真实资金，
                  在真实股票市场中，使用相同的提示和输入数据进行交易。
                </p>
                
                <h4>我们的目标</h4>
                <p>
                  我们的目标是将基准测试做得更贴近现实世界，股票市场是完美的测试环境。
                  市场是动态的、对抗性的、开放式的，并且永远不可预测。它们以静态基准测试无法做到的方式挑战AI。
                </p>
                
                <p class="highlight">市场是智能的终极考验。</p>
                
                <p>
                  那么我们需要为投资训练具有新架构的模型，还是现有的LLM就足够好了？让我们来找出答案。
                </p>
                
                <h4>参赛策略</h4>
                <ul class="contestants-list">
                  <li>DeepSeek Chat V3.1 - AI驱动多因子选股策略</li>
                  <li>Claude Sonnet 4.5 - 价值投资策略</li>
                  <li>Gemini 2.5 Pro - 技术分析策略</li>
                  <li>GPT 5 - 量化对冲策略</li>
                  <li>Grok 4 - 趋势跟踪策略</li>
                  <li>Qwen 3 Max - 机器学习策略</li>
                  <li>SPY Buy&Hold - 指数定投基准策略</li>
                </ul>
                
                <h4>比赛规则</h4>
                <ul class="rules-list">
                  <li>└─ 起始资金：每个模型获得10,000美元真实资金</li>
                  <li>└─ 交易市场：美股市场（NYSE、NASDAQ）</li>
                  <li>└─ 交易目标：最大化风险调整后收益</li>
                  <li>└─ 透明度：所有模型输出和对应交易都是公开的</li>
                  <li>└─ 自主性：每个AI必须独立产生alpha，确定交易规模、时机并管理风险</li>
                  <li>└─ 比赛时长：第一赛季将持续到2025年11月3日下午5点EST</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import NavBar from '@/components/layouts/NavBar.vue'
import CryptoPrices from '@/components/CryptoPrices.vue' // 现在显示股票价格
import ModelLeaderboard from '@/components/ModelLeaderboard.vue'
import AccountChart from '@/components/AccountChart.vue'
import ModelCard from '@/components/ModelCard.vue'

const activeTab = ref('readme')

const tabs = [
  { id: 'trades', label: 'COMPLETED TRADES' },
  { id: 'chat', label: 'MODELCHAT' },
  { id: 'positions', label: 'POSITIONS' },
  { id: 'readme', label: 'README.TXT' }
]

const models = ref([
  { 
    id: 1, 
    name: 'DEEPSEEK CHAT V3.1', 
    value: 186305.0123456789, 
    change: 86.33,
    icon: '/models/deepseek.png',
    strategy: 'AI驱动多因子选股',
    description: '基于DeepSeek大模型的智能选股策略'
  },
  { 
    id: 2, 
    name: 'CLAUDE SONNET 4.5', 
    value: 99207.0123456789, 
    change: -0.77,
    icon: '/models/claude.png',
    strategy: '价值投资策略',
    description: '专注于基本面分析的价值投资方法'
  },
  { 
    id: 3, 
    name: 'GEMINI 2.5 PRO', 
    value: 33012.3456789, 
    change: -66.99,
    icon: '/models/gemini.png',
    strategy: '技术分析策略',
    description: '基于技术指标的短线交易策略'
  },
  { 
    id: 4, 
    name: 'GROK 4', 
    value: 86809.0123456789, 
    change: -13.19,
    icon: '/models/grok.png',
    strategy: '趋势跟踪策略',
    description: '动量驱动的趋势跟踪算法'
  },
  { 
    id: 5, 
    name: 'GPT 5', 
    value: 31205.0123456789, 
    change: -68.80,
    icon: '/models/gpt5.png',
    strategy: '量化对冲策略',
    description: '多空对冲的量化交易策略'
  },
  { 
    id: 6, 
    name: 'QWEN3 MAX', 
    value: 14407.60, 
    change: 44.08,
    icon: '/models/qwen.png',
    strategy: '机器学习策略',
    description: '基于机器学习的预测模型'
  },
  { 
    id: 7, 
    name: 'SPY BUY&HOLD', 
    value: 10404.70, 
    change: 4.05,
    icon: '/models/spy.png',
    strategy: '指数定投策略',
    description: 'SPY指数买入持有基准策略'
  }
])

const selectModel = (model) => {
  console.log('Selected model:', model)
  // 处理模型选择逻辑
}
</script>

<style lang="scss" scoped>
.alpha-arena {
  min-height: 100vh;
  background: #000;
  color: #fff;
}

.main-content {
  padding-top: 80px;
  padding-bottom: 40px;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
}

.models-section {
  margin-bottom: 40px;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.tabs-section {
  background: #0a0a0a;
  border: 1px solid #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
}

.tabs {
  display: flex;
  border-bottom: 1px solid #1a1a1a;
  background: #0f0f0f;
}

.tab {
  flex: 1;
  padding: 16px 24px;
  background: none;
  border: none;
  color: #888;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
  
  &:hover {
    color: #fff;
    background: #1a1a1a;
  }
  
  &.active {
    color: #00ff88;
    border-bottom-color: #00ff88;
    background: #0a0a0a;
  }
}

.tab-content {
  padding: 32px;
  min-height: 400px;
}

.tab-panel {
  h3, h4 {
    color: #fff;
    margin-bottom: 16px;
  }
  
  h3 {
    font-size: 20px;
  }
  
  h4 {
    font-size: 16px;
    margin-top: 24px;
  }
  
  p {
    color: #ccc;
    line-height: 1.6;
    margin-bottom: 16px;
  }
}

.readme-content {
  max-width: 800px;
  
  .highlight {
    font-size: 18px;
    font-weight: 600;
    color: #00ff88;
    margin: 24px 0;
  }
  
  .contestants-list,
  .rules-list {
    list-style: none;
    padding: 0;
    margin: 16px 0;
    
    li {
      color: #ccc;
      padding: 8px 0;
      font-family: 'Courier New', monospace;
    }
  }
  
  .rules-list {
    li {
      padding: 4px 0;
    }
  }
}

@media (max-width: 768px) {
  .models-grid {
    grid-template-columns: 1fr;
  }
  
  .tabs {
    flex-wrap: wrap;
  }
  
  .tab {
    flex: 1 1 50%;
  }
}
</style>
