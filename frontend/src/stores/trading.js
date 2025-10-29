import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tradingService } from '@/services/tradingService'

export const useTradingStore = defineStore('trading', () => {
  // 状态
  const positions = ref([])
  const orders = ref([])
  const marketData = ref({})
  const isConnected = ref(false)

  // 计算属性
  const totalValue = computed(() => {
    return positions.value.reduce((total, position) => {
      return total + (position.quantity * position.currentPrice)
    }, 0)
  })

  const totalPnL = computed(() => {
    return positions.value.reduce((total, position) => {
      return total + position.unrealizedPnL
    }, 0)
  })

  // 动作
  const fetchPositions = async () => {
    try {
      const data = await tradingService.getPositions()
      positions.value = data
    } catch (error) {
      console.error('获取持仓失败:', error)
    }
  }

  const fetchOrders = async () => {
    try {
      const data = await tradingService.getOrders()
      orders.value = data
    } catch (error) {
      console.error('获取订单失败:', error)
    }
  }

  const createOrder = async (orderData) => {
    try {
      const order = await tradingService.createOrder(orderData)
      orders.value.unshift(order)
      return order
    } catch (error) {
      console.error('创建订单失败:', error)
      throw error
    }
  }

  const cancelOrder = async (orderId) => {
    try {
      await tradingService.cancelOrder(orderId)
      const index = orders.value.findIndex(order => order.id === orderId)
      if (index > -1) {
        orders.value[index].status = 'cancelled'
      }
    } catch (error) {
      console.error('撤销订单失败:', error)
      throw error
    }
  }

  const updateMarketData = (symbol, data) => {
    marketData.value[symbol] = {
      ...marketData.value[symbol],
      ...data,
      timestamp: new Date()
    }
  }

  const connectWebSocket = () => {
    // WebSocket连接逻辑
    isConnected.value = true
  }

  const disconnectWebSocket = () => {
    isConnected.value = false
  }

  return {
    // 状态
    positions,
    orders,
    marketData,
    isConnected,
    // 计算属性
    totalValue,
    totalPnL,
    // 动作
    fetchPositions,
    fetchOrders,
    createOrder,
    cancelOrder,
    updateMarketData,
    connectWebSocket,
    disconnectWebSocket
  }
})
