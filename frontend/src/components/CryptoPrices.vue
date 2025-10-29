<template>
  <div class="stock-prices">
    <div 
      v-for="stock in stocks" 
      :key="stock.symbol" 
      class="stock-item"
    >
      <div class="stock-info">
        <img :src="stock.icon" :alt="stock.symbol" class="stock-icon" />
        <span class="stock-symbol">{{ stock.symbol }}</span>
      </div>
      <div class="stock-price">
        <span class="dollar-sign">$</span>
        <span class="price-value">{{ formatPrice(stock.price) }}</span>
        <span 
          :class="['price-change', stock.change >= 0 ? 'positive' : 'negative']"
        >
          {{ stock.change >= 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}%
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { stockService } from '@/services/stockService'
import { websocketService } from '@/services/websocketService'

const stocks = ref([
  { symbol: 'AAPL', price: 150.25, change: 1.25, icon: '/stocks/aapl.svg' },
  { symbol: 'MSFT', price: 320.45, change: -0.85, icon: '/stocks/msft.svg' },
  { symbol: 'GOOGL', price: 2800.12, change: 2.15, icon: '/stocks/googl.svg' },
  { symbol: 'TSLA', price: 245.67, change: -1.45, icon: '/stocks/tsla.svg' },
  { symbol: 'NVDA', price: 420.89, change: 3.25, icon: '/stocks/nvda.svg' },
  { symbol: 'AMZN', price: 3150.33, change: 0.75, icon: '/stocks/amzn.svg' }
])

let priceUpdateInterval = null

const formatPrice = (price) => {
  if (price >= 1000) {
    return price.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })
  } else if (price >= 1) {
    return price.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 4 
    })
  } else {
    return price.toFixed(4)
  }
}

const fetchStockPrices = async () => {
  try {
    const data = await stockService.getStockPrices()
    if (data && data.length > 0) {
      stocks.value = data
    }
  } catch (error) {
    console.error('获取股票价格失败:', error)
  }
}

onMounted(async () => {
  // 初始获取数据
  await fetchStockPrices()
  
  // 设置定时更新（备用方案）
  priceUpdateInterval = setInterval(fetchStockPrices, 30000) // 每30秒更新一次
  
  // 订阅WebSocket实时数据
  const symbols = stocks.value.map(stock => stock.symbol)
  websocketService.subscribeStockPrices(symbols, (data) => {
    const stockIndex = stocks.value.findIndex(stock => stock.symbol === data.symbol)
    if (stockIndex !== -1) {
      stocks.value[stockIndex] = {
        ...stocks.value[stockIndex],
        price: data.price,
        change: data.change
      }
    }
  })
})

onUnmounted(() => {
  if (priceUpdateInterval) {
    clearInterval(priceUpdateInterval)
  }
  
  // 取消WebSocket订阅
  const symbols = stocks.value.map(stock => stock.symbol)
  symbols.forEach(symbol => {
    websocketService.unsubscribe('stock_prices')
  })
})
</script>

<style lang="scss" scoped>
.stock-prices {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 32px;
}

.stock-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #0a0a0a;
  border: 1px solid #1a1a1a;
  border-radius: 8px;
  min-width: 200px;
  transition: all 0.2s;
  
  &:hover {
    border-color: #00ff88;
    background: #0f0f0f;
  }
}

.stock-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-icon {
  width: 24px;
  height: 24px;
}

.stock-symbol {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.stock-price {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.dollar-sign {
  font-size: 14px;
  color: #888;
  margin-right: 2px;
}

.price-value {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  font-variant-numeric: tabular-nums;
}

.price-change {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
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
</style>
