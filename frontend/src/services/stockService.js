import api from './api'

export const stockService = {
  // 获取股票价格列表
  async getStockPrices() {
    try {
      const response = await api.get('/market-data/stocks')
      return response.data || []
    } catch (error) {
      console.error('获取股票价格失败:', error)
      throw error
    }
  },

  // 获取单个股票详细信息
  async getStockDetail(symbol) {
    try {
      const response = await api.get(`/market-data/stocks/${symbol}`)
      return response.data
    } catch (error) {
      console.error(`获取股票 ${symbol} 详情失败:`, error)
      throw error
    }
  },

  // 获取股票历史数据
  async getStockHistory(symbol, timeframe = '1d') {
    try {
      const response = await api.get(`/market-data/stocks/${symbol}/history`, {
        params: { timeframe }
      })
      return response.data
    } catch (error) {
      console.error(`获取股票 ${symbol} 历史数据失败:`, error)
      throw error
    }
  },

  // 获取实时股票数据（WebSocket）
  subscribeToStockUpdates(symbols, callback) {
    const ws = new WebSocket(`ws://localhost:8000/ws/market-data/stocks`)
    
    ws.onopen = () => {
      console.log('WebSocket连接已建立')
      // 订阅指定股票
      ws.send(JSON.stringify({
        type: 'subscribe',
        symbols: symbols
      }))
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        callback(data)
      } catch (error) {
        console.error('解析WebSocket数据失败:', error)
      }
    }
    
    ws.onclose = () => {
      console.log('WebSocket连接已关闭')
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
    }
    
    return ws
  }
}
