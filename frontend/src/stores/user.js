import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const isAuthenticated = ref(false)
  const user = ref(null)

  const initialize = () => {
    // 初始化用户状态
    console.log('User store initialized')
  }

  const login = async (credentials) => {
    // 登录逻辑
    isAuthenticated.value = true
  }

  const logout = () => {
    isAuthenticated.value = false
    user.value = null
  }

  return {
    isAuthenticated,
    user,
    initialize,
    login,
    logout
  }
})
