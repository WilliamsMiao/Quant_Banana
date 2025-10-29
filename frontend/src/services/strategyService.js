import api from './api'

export const strategyService = {
  // 获取策略列表
  async getStrategies() {
    try {
      const response = await api.get('/strategies')
      return response.data || []
    } catch (error) {
      console.error('获取策略列表失败:', error)
      throw error
    }
  },

  // 获取策略详情
  async getStrategyDetail(strategyId) {
    try {
      const response = await api.get(`/strategies/${strategyId}`)
      return response.data
    } catch (error) {
      console.error(`获取策略 ${strategyId} 详情失败:`, error)
      throw error
    }
  },

  // 创建策略
  async createStrategy(strategyData) {
    try {
      const response = await api.post('/strategies', strategyData)
      return response.data
    } catch (error) {
      console.error('创建策略失败:', error)
      throw error
    }
  },

  // 更新策略
  async updateStrategy(strategyId, strategyData) {
    try {
      const response = await api.put(`/strategies/${strategyId}`, strategyData)
      return response.data
    } catch (error) {
      console.error(`更新策略 ${strategyId} 失败:`, error)
      throw error
    }
  },

  // 启动策略
  async startStrategy(strategyId) {
    try {
      const response = await api.post(`/strategies/${strategyId}/start`)
      return response.data
    } catch (error) {
      console.error(`启动策略 ${strategyId} 失败:`, error)
      throw error
    }
  },

  // 停止策略
  async stopStrategy(strategyId) {
    try {
      const response = await api.post(`/strategies/${strategyId}/stop`)
      return response.data
    } catch (error) {
      console.error(`停止策略 ${strategyId} 失败:`, error)
      throw error
    }
  },

  // 获取策略性能指标
  async getStrategyPerformance(strategyId) {
    try {
      const response = await api.get(`/strategies/${strategyId}/performance`)
      return response.data
    } catch (error) {
      console.error(`获取策略 ${strategyId} 性能指标失败:`, error)
      throw error
    }
  }
}
