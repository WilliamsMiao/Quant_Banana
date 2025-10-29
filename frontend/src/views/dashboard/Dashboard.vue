<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 市场概览 -->
      <el-col :span="24">
        <el-card class="market-overview">
          <template #header>
            <div class="card-header">
              <span>市场概览</span>
              <el-button type="primary" size="small" @click="refreshMarketData">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          <MarketOverview />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 组合摘要 -->
      <el-col :span="12">
        <el-card class="portfolio-summary">
          <template #header>
            <div class="card-header">
              <span>组合摘要</span>
            </div>
          </template>
          <PortfolioSummary />
        </el-card>
      </el-col>

      <!-- 实时图表 -->
      <el-col :span="12">
        <el-card class="real-time-chart">
          <template #header>
            <div class="card-header">
              <span>实时图表</span>
            </div>
          </template>
          <RealTimeChart />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MarketOverview from '@/components/dashboard/MarketOverview.vue'
import PortfolioSummary from '@/components/dashboard/PortfolioSummary.vue'
import RealTimeChart from '@/components/charts/RealTimeChart.vue'

const refreshMarketData = () => {
  // 刷新市场数据逻辑
  console.log('刷新市场数据')
}
</script>

<style lang="scss" scoped>
.dashboard {
  padding: 20px;
  height: 100vh;
  overflow-y: auto;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .market-overview,
  .portfolio-summary,
  .real-time-chart {
    height: 400px;
  }
}
</style>
