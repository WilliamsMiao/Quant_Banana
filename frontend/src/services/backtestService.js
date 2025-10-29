import api from './api'

export const backtestService = {
  // 运行回测
  async runBacktest(backtestConfig) {
    try {
      const response = await api.post('/backtesting/run', backtestConfig)
      return response.data
    } catch (error) {
      console.error('运行回测失败:', error)
      throw error
    }
  },

  // 获取回测结果
  async getBacktestResults(backtestId) {
    try {
      const response = await api.get(`/backtesting/results/${backtestId}`)
      return response.data
    } catch (error) {
      console.error(`获取回测结果 ${backtestId} 失败:`, error)
      throw error
    }
  },

  // 获取回测性能指标
  async getBacktestPerformance(backtestId) {
    try {
      const response = await api.get(`/backtesting/performance/${backtestId}`)
      return response.data
    } catch (error) {
      console.error(`获取回测性能指标 ${backtestId} 失败:`, error)
      throw error
    }
  },

  // 获取回测历史
  async getBacktestHistory(params = {}) {
    try {
      const response = await api.get('/backtesting/history', { params })
      return response.data || []
    } catch (error) {
      console.error('获取回测历史失败:', error)
      throw error
    }
  }
}
