<template>
  <div class="account-chart">
    <div class="chart-header">
      <div class="time-filters">
        <button 
          v-for="filter in timeFilters" 
          :key="filter"
          :class="['time-filter', { active: selectedTimeFilter === filter }]"
          @click="selectedTimeFilter = filter"
        >
          {{ filter }}
        </button>
      </div>
      <div class="value-filters">
        <button 
          v-for="filter in valueFilters" 
          :key="filter"
          :class="['value-filter', { active: selectedValueFilter === filter }]"
          @click="selectedValueFilter = filter"
        >
          {{ filter }}
        </button>
      </div>
      <h2 class="chart-title">TOTAL ACCOUNT VALUE</h2>
    </div>
    <div class="chart-container" ref="chartContainer">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { backtestService } from '@/services/backtestService'
import { websocketService } from '@/services/websocketService'

const chartContainer = ref(null)
const chartCanvas = ref(null)
const selectedTimeFilter = ref('ALL')
const selectedValueFilter = ref('$')

const timeFilters = ['ALL', '72H']
const valueFilters = ['$', '%']

// 获取策略性能数据
const fetchChartData = async () => {
  try {
    const data = await backtestService.getBacktestHistory({
      limit: 30,
      timeframe: selectedTimeFilter.value === 'ALL' ? '1d' : '1h'
    })
    return data.map(item => ({
      date: new Date(item.timestamp),
      value: item.account_value,
      strategy: item.strategy_name
    }))
  } catch (error) {
    console.error('获取图表数据失败:', error)
    return generateMockData()
  }
}

// 生成模拟数据（备用）
const generateMockData = () => {
  const data = []
  const now = Date.now()
  const days = selectedTimeFilter.value === 'ALL' ? 30 : 3
  
  for (let i = days; i >= 0; i--) {
    const date = new Date(now - i * 24 * 60 * 60 * 1000)
    const value = 10000 + Math.random() * 8000 + Math.sin(i / 5) * 3000
    data.push({ date, value, strategy: 'DeepSeek Chat V3.1' })
  }
  
  return data
}

const drawChart = async () => {
  if (!chartCanvas.value || !chartContainer.value) return
  
  const canvas = chartCanvas.value
  const ctx = canvas.getContext('2d')
  const container = chartContainer.value
  
  canvas.width = container.clientWidth
  canvas.height = container.clientHeight
  
  const data = await fetchChartData()
  const padding = { top: 40, right: 40, bottom: 40, left: 60 }
  const width = canvas.width - padding.left - padding.right
  const height = canvas.height - padding.top - padding.bottom
  
  // 清除画布
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  if (data.length === 0) return
  
  // 计算数据范围
  const values = data.map(d => d.value)
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const valueRange = maxValue - minValue || 1
  
  // 绘制网格
  ctx.strokeStyle = '#1a1a1a'
  ctx.lineWidth = 1
  
  // 绘制Y轴标签和网格线
  const ySteps = 5
  for (let i = 0; i <= ySteps; i++) {
    const y = padding.top + (height / ySteps) * i
    const value = maxValue - (valueRange / ySteps) * i
    
    ctx.strokeStyle = '#1a1a1a'
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(padding.left + width, y)
    ctx.stroke()
    
    ctx.fillStyle = '#888'
    ctx.font = '12px monospace'
    ctx.textAlign = 'right'
    ctx.fillText(`$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`, padding.left - 10, y + 4)
  }
  
  // 绘制X轴标签
  const xSteps = Math.min(5, data.length)
  for (let i = 0; i < xSteps; i++) {
    const index = Math.floor((data.length - 1) * i / (xSteps - 1))
    const x = padding.left + (width / (data.length - 1)) * index
    const date = data[index].date
    
    ctx.fillStyle = '#888'
    ctx.font = '10px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(date.toLocaleDateString(), x, canvas.height - 10)
  }
  
  // 绘制数据线
  ctx.strokeStyle = '#00ff88'
  ctx.lineWidth = 2
  ctx.beginPath()
  
  data.forEach((point, index) => {
    const x = padding.left + (width / (data.length - 1)) * index
    const normalizedValue = (point.value - minValue) / valueRange
    const y = padding.top + height * (1 - normalizedValue)
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // 绘制数据点
  ctx.fillStyle = '#00ff88'
  data.forEach((point, index) => {
    const x = padding.left + (width / (data.length - 1)) * index
    const normalizedValue = (point.value - minValue) / valueRange
    const y = padding.top + height * (1 - normalizedValue)
    
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, Math.PI * 2)
    ctx.fill()
  })
}

onMounted(async () => {
  await drawChart()
  window.addEventListener('resize', drawChart)
  
  // 订阅实时数据更新
  websocketService.subscribe('account_value_updates', (data) => {
    drawChart()
  })
})

watch([selectedTimeFilter, selectedValueFilter], async () => {
  await drawChart()
})
</script>

<style lang="scss" scoped>
.account-chart {
  background: #0a0a0a;
  border: 1px solid #1a1a1a;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 32px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.time-filters,
.value-filters {
  display: flex;
  gap: 8px;
}

.time-filter,
.value-filter {
  background: #1a1a1a;
  border: 1px solid #333;
  color: #fff;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: #00ff88;
    color: #00ff88;
  }
  
  &.active {
    background: #00ff88;
    border-color: #00ff88;
    color: #000;
  }
}

.chart-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.chart-container {
  width: 100%;
  height: 400px;
  position: relative;
}

canvas {
  width: 100%;
  height: 100%;
}
</style>
