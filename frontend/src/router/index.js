import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'AlphaArena',
    component: () => import('@/views/AlphaArena.vue')
  },
  {
    path: '/leaderboard',
    name: 'Leaderboard',
    component: () => import('@/views/Leaderboard.vue')
  },
  {
    path: '/blog',
    name: 'Blog',
    component: () => import('@/views/Blog.vue')
  },
  {
    path: '/waitlist',
    name: 'Waitlist',
    component: () => import('@/views/Waitlist.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
