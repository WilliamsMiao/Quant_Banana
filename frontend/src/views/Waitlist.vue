<template>
  <div class="waitlist-page">
    <NavBar />
    <main class="main-content">
      <div class="container">
        <h1>Join The Platform Waitlist</h1>
        <p>等待列表页面</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import NavBar from '@/components/layouts/NavBar.vue'
</script>

<style lang="scss" scoped>
.waitlist-page {
  min-height: 100vh;
  background: #000;
  color: #fff;
}

.main-content {
  padding-top: 80px;
  padding-bottom: 40px;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
}
</style>
