<template>
  <div class="model-card" @click="handleClick">
    <div class="model-header">
      <img :src="model.icon" :alt="model.name" class="model-icon" />
      <div class="model-info">
        <h3 class="model-name">{{ model.name }}</h3>
        <p class="model-strategy">{{ model.strategy }}</p>
      </div>
    </div>
    <div class="model-metrics">
      <div class="model-value">
        <span class="dollar-sign">$</span>
        <span class="amount">{{ formatPrice(model.value) }}</span>
      </div>
      <div 
        :class="['model-change', model.change >= 0 ? 'positive' : 'negative']"
      >
        {{ model.change >= 0 ? '+' : '' }}{{ model.change.toFixed(2) }}%
      </div>
    </div>
    <p class="model-description">{{ model.description }}</p>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  model: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['click'])

const formatPrice = (price) => {
  return price.toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 10 
  })
}

const handleClick = () => {
  emit('click', props.model)
}
</script>

<style lang="scss" scoped>
.model-card {
  background: #0a0a0a;
  border: 1px solid #1a1a1a;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: #00ff88;
    background: #0f0f0f;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 255, 136, 0.1);
  }
}

.model-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.model-icon {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  flex-shrink: 0;
}

.model-info {
  flex: 1;
}

.model-name {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 4px 0;
  line-height: 1.2;
}

.model-strategy {
  font-size: 12px;
  color: #888;
  margin: 0;
  font-weight: 500;
}

.model-metrics {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.model-value {
  display: flex;
  align-items: baseline;
}

.dollar-sign {
  font-size: 16px;
  color: #888;
  margin-right: 2px;
}

.amount {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  font-variant-numeric: tabular-nums;
}

.model-change {
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

.model-description {
  font-size: 12px;
  color: #aaa;
  margin: 0;
  line-height: 1.4;
}
</style>
