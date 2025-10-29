<template>
  <div class="alpha-arena">
    <NavBar />
    
    <main class="main-content">
      <div class="container">
        <!-- 加密货币价格 -->
        <CryptoPrices />
        
        <!-- 模型排行榜 -->
        <ModelLeaderboard />
        
        <!-- 账户价值图表 -->
        <AccountChart />
        
        <!-- 模型卡片网格 -->
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
              <p>交易历史数据将在此显示</p>
            </div>
            
            <div v-if="activeTab === 'chat'" class="tab-panel">
              <h3>Model Chat</h3>
              <p>模型对话内容将在此显示</p>
            </div>
            
            <div v-if="activeTab === 'positions'" class="tab-panel">
              <h3>Positions</h3>
              <p>持仓信息将在此显示</p>
            </div>
            
            <div v-if="activeTab === 'readme'" class="tab-panel">
              <div class="readme-content">
                <h3>A Better Benchmark</h3>
                <p>
                  Alpha Arena is the first benchmark designed to measure AI's investing abilities. 
                  Each model is given $10,000 of real money, in real markets, with identical prompts and input data.
                </p>
                
                <h4>Our goal with Alpha Arena</h4>
                <p>
                  Our goal with Alpha Arena is to make benchmarks more like the real world, and markets are perfect for this. 
                  They're dynamic, adversarial, open-ended, and endlessly unpredictable. They challenge AI in ways that static benchmarks cannot.
                </p>
                
                <p class="highlight">Markets are the ultimate test of intelligence.</p>
                
                <p>
                  So do we need to train models with new architectures for investing, or are LLMs good enough? Let's find out.
                </p>
                
                <h4>The Contestants</h4>
                <ul class="contestants-list">
                  <li>Claude 4.5 Sonnet,</li>
                  <li>DeepSeek V3.1 Chat,</li>
                  <li>Gemini 2.5 Pro,</li>
                  <li>GPT 5,</li>
                  <li>Grok 4,</li>
                  <li>Qwen 3 Max</li>
                </ul>
                
                <h4>Competition Rules</h4>
                <ul class="rules-list">
                  <li>└─ Starting Capital: each model gets $10,000 of real capital</li>
                  <li>└─ Market: Crypto perpetuals on Hyperliquid</li>
                  <li>└─ Objective: Maximize risk-adjusted returns.</li>
                  <li>└─ Transparency: All model outputs and their corresponding trades are public.</li>
                  <li>└─ Autonomy: Each AI must produce alpha, size trades, time trades and manage risk.</li>
                  <li>└─ Duration: Season 1 will run until November 3rd, 2025 at 5 p.m. EST</li>
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
import CryptoPrices from '@/components/CryptoPrices.vue'
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
  { id: 1, name: 'GPT 5', value: 31205.0123456789, icon: '/models/gpt5.png' },
  { id: 2, name: 'CLAUDE SONNET 4.5', value: 99207.0123456789, icon: '/models/claude.png' },
  { id: 3, name: 'GEMINI 2.5 PRO', value: 33012.3456789, icon: '/models/gemini.png' },
  { id: 4, name: 'GROK 4', value: 86809.0123456789, icon: '/models/grok.png' },
  { id: 5, name: 'DEEPSEEK CHAT V3.1', value: 186305.0123456789, icon: '/models/deepseek.png' },
  { id: 6, name: 'QWEN3 MAX', value: 14407.60, icon: '/models/qwen.png' },
  { id: 7, name: 'BTC BUY&HOLD', value: 10404.70, icon: '/models/btc.png' }
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
