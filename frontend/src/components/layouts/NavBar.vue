<template>
  <nav class="navbar">
    <div class="navbar-container">
      <div class="navbar-left">
        <router-link to="/" class="logo-link">
          <img src="/logo.svg" alt="Alpha Arena" class="logo" />
          <span class="logo-text">Alpha Arena</span>
        </router-link>
        <div class="nav-links">
          <router-link to="/" class="nav-link">LIVE</router-link>
          <span class="divider">|</span>
          <router-link to="/leaderboard" class="nav-link">LEADERBOARD</router-link>
          <span class="divider">|</span>
          <router-link to="/blog" class="nav-link">BLOG</router-link>
          <span class="divider">|</span>
          <button class="nav-button" @click="showModels">MODELS</button>
        </div>
      </div>
      <div class="navbar-right">
        <router-link to="/waitlist" class="cta-link waitlist">
          JOIN THE PLATFORM WAITLIST
          <img src="/arrow.svg" alt="arrow" class="arrow-icon" />
        </router-link>
        <a href="https://thenof1.com" target="_blank" class="cta-link about">
          ABOUT NOF1
          <img src="/arrow.svg" alt="arrow" class="arrow-icon" />
        </a>
      </div>
    </div>
  </nav>
</template>

<script setup>
const showModels = () => {
  // 显示模型列表
  console.log('Show models')
}
</script>

<style lang="scss" scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: #000;
  border-bottom: 1px solid #1a1a1a;
  padding: 0;
}

.navbar-container {
  max-width: 1920px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo-link {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: #fff;
  
  .logo {
    height: 24px;
    width: auto;
  }
  
  .logo-text {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-link {
  color: #fff;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  padding: 8px 12px;
  transition: color 0.2s;
  
  &:hover, &.router-link-active {
    color: #00ff88;
  }
}

.divider {
  color: #444;
  font-size: 14px;
}

.nav-button {
  background: none;
  border: none;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  padding: 8px 12px;
  cursor: pointer;
  transition: color 0.2s;
  
  &:hover {
    color: #00ff88;
  }
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.cta-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  text-decoration: none;
  font-size: 12px;
  font-weight: 500;
  padding: 8px 16px;
  border: 1px solid #333;
  border-radius: 4px;
  transition: all 0.2s;
  
  &:hover {
    border-color: #00ff88;
    color: #00ff88;
  }
  
  .arrow-icon {
    width: 12px;
    height: 12px;
    opacity: 0.7;
  }
  
  &.waitlist {
    background: #00ff88;
    color: #000;
    border-color: #00ff88;
    
    &:hover {
      background: #00dd77;
    }
  }
}

@media (max-width: 768px) {
  .navbar-container {
    flex-direction: column;
    gap: 12px;
  }
  
  .nav-links {
    flex-wrap: wrap;
  }
  
  .navbar-right {
    flex-wrap: wrap;
  }
}
</style>
