<template>
  <div class="model-card" @click="handleClick">
    <div class="model-header">
      <img :src="model.icon" :alt="model.name" class="model-icon" />
      <h3 class="model-name">{{ model.name }}</h3>
    </div>
    <div class="model-value">
      <span class="dollar-sign">$</span>
      <span class="amount">{{ formatPrice(model.value) }}</span>
    </div>
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
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: #00ff88;
    background: #0f0f0f;
    transform: translateY(-2px);
  }
}

.model-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.model-icon {
  width: 32px;
  height: 32px;
  border-radius: 4px;
}

.model-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.model-value {
  display: flex;
  align-items: baseline;
}

.dollar-sign {
  font-size: 14px;
  color: #888;
  margin-right: 2px;
}

.amount {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  font-variant-numeric: tabular-nums;
}
</style>
