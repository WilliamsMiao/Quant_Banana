<template>
  <div class="crypto-prices">
    <div 
      v-for="crypto in cryptos" 
      :key="crypto.symbol" 
      class="crypto-item"
    >
      <div class="crypto-info">
        <img :src="crypto.icon" :alt="crypto.symbol" class="crypto-icon" />
        <span class="crypto-symbol">{{ crypto.symbol }}</span>
      </div>
      <div class="crypto-price">
        <span class="dollar-sign">$</span>
        <span class="price-value">{{ formatPrice(crypto.price) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const cryptos = ref([
  { symbol: 'BTC', price: 111174.50, icon: '/crypto/btc.svg' },
  { symbol: 'ETH', price: 3967.0123456789, icon: '/crypto/eth.svg' },
  { symbol: 'SOL', price: 195.0123456789, icon: '/crypto/sol.svg' },
  { symbol: 'BNB', price: 1100.0123456789, icon: '/crypto/bnb.svg' },
  { symbol: 'DOGE', price: 0.1920, icon: '/crypto/doge.svg' },
  { symbol: 'XRP', price: 0.62, icon: '/crypto/xrp.svg' }
])

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

// 模拟实时价格更新
onMounted(() => {
  setInterval(() => {
    cryptos.value.forEach(crypto => {
      const change = (Math.random() - 0.5) * crypto.price * 0.001
      crypto.price = Math.max(0.0001, crypto.price + change)
    })
  }, 1000)
})
</script>

<style lang="scss" scoped>
.crypto-prices {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 32px;
}

.crypto-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #0a0a0a;
  border: 1px solid #1a1a1a;
  border-radius: 8px;
  min-width: 180px;
}

.crypto-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.crypto-icon {
  width: 24px;
  height: 24px;
}

.crypto-symbol {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.crypto-price {
  display: flex;
  align-items: baseline;
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
</style>
