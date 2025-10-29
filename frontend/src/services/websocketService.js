class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectInterval = 5000
    this.listeners = new Map()
  }

  connect() {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    
    try {
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log('WebSocket连接已建立')
        this.reconnectAttempts = 0
        this.emit('connected')
      }
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
        }
      }
      
      this.ws.onclose = (event) => {
        console.log('WebSocket连接已关闭:', event.code, event.reason)
        this.emit('disconnected')
        this.attemptReconnect()
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        this.emit('error', error)
      }
    } catch (error) {
      console.error('创建WebSocket连接失败:', error)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`尝试重连WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      
      setTimeout(() => {
        this.connect()
      }, this.reconnectInterval)
    } else {
      console.error('WebSocket重连失败，已达到最大重连次数')
      this.emit('reconnect_failed')
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket未连接，无法发送消息')
    }
  }

  subscribe(topic, callback) {
    if (!this.listeners.has(topic)) {
      this.listeners.set(topic, new Set())
    }
    this.listeners.get(topic).add(callback)
    
    // 发送订阅消息
    this.send({
      type: 'subscribe',
      topic: topic
    })
  }

  unsubscribe(topic, callback) {
    if (this.listeners.has(topic)) {
      this.listeners.get(topic).delete(callback)
      
      // 如果没有监听器了，发送取消订阅消息
      if (this.listeners.get(topic).size === 0) {
        this.send({
          type: 'unsubscribe',
          topic: topic
        })
      }
    }
  }

  handleMessage(data) {
    const { type, topic, payload } = data
    
    switch (type) {
      case 'market_data':
        this.emit('market_data', payload)
        break
      case 'order_update':
        this.emit('order_update', payload)
        break
      case 'strategy_signal':
        this.emit('strategy_signal', payload)
        break
      case 'system_alert':
        this.emit('system_alert', payload)
        break
      default:
        if (topic && this.listeners.has(topic)) {
          this.listeners.get(topic).forEach(callback => {
            callback(payload)
          })
        }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        callback(data)
      })
    }
  }

  // 订阅股票价格更新
  subscribeStockPrices(symbols, callback) {
    this.subscribe('stock_prices', (data) => {
      if (symbols.includes(data.symbol)) {
        callback(data)
      }
    })
  }

  // 订阅策略信号
  subscribeStrategySignals(strategyId, callback) {
    this.subscribe(`strategy_${strategyId}`, callback)
  }

  // 订阅订单更新
  subscribeOrderUpdates(callback) {
    this.subscribe('order_updates', callback)
  }

  // 订阅持仓更新
  subscribePositionUpdates(callback) {
    this.subscribe('position_updates', callback)
  }
}

// 创建单例实例
export const websocketService = new WebSocketService()

// 自动连接
websocketService.connect()

export default websocketService
