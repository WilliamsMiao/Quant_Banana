import api from './api'

export const tradingService = {
  // 获取账户信息
  async getAccountInfo() {
    try {
      const response = await api.get('/trading/account')
      return response.data
    } catch (error) {
      console.error('获取账户信息失败:', error)
      throw error
    }
  },

  // 获取持仓列表
  async getPositions() {
    try {
      const response = await api.get('/trading/positions')
      return response.data || []
    } catch (error) {
      console.error('获取持仓失败:', error)
      throw error
    }
  },

  // 获取订单列表
  async getOrders() {
    try {
      const response = await api.get('/trading/orders')
      return response.data || []
    } catch (error) {
      console.error('获取订单失败:', error)
      throw error
    }
  },

  // 创建订单
  async createOrder(orderData) {
    try {
      const response = await api.post('/trading/orders', orderData)
      return response.data
    } catch (error) {
      console.error('创建订单失败:', error)
      throw error
    }
  },

  // 撤销订单
  async cancelOrder(orderId) {
    try {
      const response = await api.delete(`/trading/orders/${orderId}`)
      return response.data
    } catch (error) {
      console.error('撤销订单失败:', error)
      throw error
    }
  },

  // 获取交易历史
  async getTradeHistory(params = {}) {
    try {
      const response = await api.get('/trading/trades', { params })
      return response.data || []
    } catch (error) {
      console.error('获取交易历史失败:', error)
      throw error
    }
  }
}
