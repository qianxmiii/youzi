import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
          meta: { title: '工作台' },
        },
        {
          path: 'box',
          name: 'box',
          component: () => import('@/views/PlaceholderView.vue'),
          meta: { title: '箱规计算', migration: 'index.html 箱规模块' },
        },
        {
          path: 'quote',
          name: 'quote',
          component: () => import('@/views/PlaceholderView.vue'),
          meta: { title: '单地址报价', migration: 'logistics.js updateQuote' },
        },
        {
          path: 'quote/batch',
          name: 'quote-batch',
          component: () => import('@/views/PlaceholderView.vue'),
          meta: { title: '批量报价', migration: 'generateBatchQuote' },
        },
        {
          path: 'cost',
          name: 'cost',
          component: () => import('@/views/PlaceholderView.vue'),
          meta: { title: '成本计算', migration: 'tab.js calculateCost*' },
        },
        {
          path: 'library',
          name: 'library',
          component: () => import('@/views/PlaceholderView.vue'),
          meta: { title: '资料库', migration: '术语 / 网址 / 备忘录' },
        },
        {
          path: 'addresses',
          name: 'addresses',
          component: () => import('@/views/PlaceholderView.vue'),
          meta: { title: '地址簿', migration: '/api/addresses' },
        },
        {
          path: 'shipments',
          name: 'shipments',
          component: () => import('@/views/shipments/ShipmentsView.vue'),
          meta: { title: '运单管理' },
        },
        {
          path: 'statistics',
          name: 'statistics',
          component: () => import('@/views/statistics/StatisticsView.vue'),
          meta: { title: '统计管理' },
        },
        {
          path: 'admin',
          name: 'admin',
          component: () => import('@/views/admin/AdminCodeTablesView.vue'),
          meta: { title: '后台管理' },
        },
        {
          path: 'customers',
          name: 'customers',
          component: () => import('@/views/admin/CustomersView.vue'),
          meta: { title: '客户管理' },
        },
        {
          path: 'channels',
          name: 'channels',
          component: () => import('@/views/channels/ChannelsView.vue'),
          meta: { title: '渠道管理' },
        },
        {
          path: 'scheduled-tasks',
          name: 'scheduled-tasks',
          component: () => import('@/views/scheduled/ScheduledTasksView.vue'),
          meta: { title: '计划任务' },
        },
      ],
    },
  ],
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || 'Youzi'
  document.title = `${title} · Youzi`
})

export default router
