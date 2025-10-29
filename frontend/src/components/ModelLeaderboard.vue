<template>
  <div class="leaderboard">
    <div class="leaderboard-header">
      <div class="highest">
        <span class="label">HIGHEST:</span>
        <img src="/models/deepseek.png" alt="DeepSeek" class="model-icon" />
        <span class="model-name">DEEPSEEK CHAT V3.1</span>
        <div class="value">
          <span class="dollar-sign">$</span>
          <span class="amount">{{ formatPrice(highest.value) }}</span>
        </div>
        <span class="percentage positive">+{{ highest.percentage }}%</span>
      </div>
      <span class="divider">|</span>
      <div class="lowest">
        <span class="label">LOWEST:</span>
        <img src="/models/gpt5.png" alt="GPT-5" class="model-icon" />
        <span class="model-name">GPT 5</span>
        <div class="value">
          <span class="dollar-sign">$</span>
          <span class="amount">{{ formatPrice(lowest.value) }}</span>
        </div>
        <span class="percentage negative">{{ lowest.percentage }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const highest = ref({
  value: 186305.0123456789,
  percentage: 86.33
})

const lowest = ref({
  value: 31205.0123456789,
  percentage: -68.71
})

const formatPrice = (price) => {
  return price.toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 10 
  })
}
</script>

<style lang="scss" scoped>
.leaderboard {
  margin-bottom: 32px;
}

.leaderboard-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #0a0a0a;
  border: 1px solid #1a1a1a;
  border-radius: 8px;
}

.highest,
.lowest {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.label {
  font-size: 12px;
  color: #888;
  font-weight: 500;
}

.model-icon {
  width: 24px;
  height: 24px;
  border-radius: 4px;
}

.model-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.value {
  display: flex;
  align-items: baseline;
  margin-left: auto;
  margin-right: 12px;
}

.dollar-sign {
  font-size: 14px;
  color: #888;
  margin-right: 2px;
}

.amount {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  font-variant-numeric: tabular-nums;
}

.percentage {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  
  &.positive {
    color: #00ff88;
    background: rgba(0, 255, 136, 0.1);
  }
  
  &.negative {
    color: #ff4444;
    background: rgba(255, 68, 68, 0.1);
  }
}

.divider {
  color: #444;
  font-size: 16px;
}

@media (max-width: 768px) {
  .leaderboard-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .divider {
    display: none;
  }
}
</style>
