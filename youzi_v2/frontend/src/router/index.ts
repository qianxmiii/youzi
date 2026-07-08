import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import { usePageTabs } from '@/composables/usePageTabs'

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
          component: () => import('@/views/cost/CostCalculationView.vue'),
          meta: { title: '成本计算' },
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
          component: () => import('@/views/addresses/AddressesView.vue'),
          meta: { title: '地址簿' },
        },
        {
          path: 'shipments',
          name: 'shipments',
          component: () => import('@/views/shipments/ShipmentsView.vue'),
          meta: { title: '运单管理' },
        },
        {
          path: 'shipment-exceptions',
          name: 'shipment-exceptions',
          component: () => import('@/views/shipment-exceptions/ShipmentExceptionsView.vue'),
          meta: { title: '异常跟踪' },
        },
        {
          path: 'shipment-groups',
          name: 'shipment-groups',
          component: () => import('@/views/shipment-groups/ShipmentGroupsView.vue'),
          meta: { title: '运单分组' },
        },
        {
          path: 'vessel-schedules',
          name: 'vessel-schedules',
          component: () => import('@/views/vessel-schedules/VesselSchedulesView.vue'),
          meta: { title: '船期监控' },
        },
        {
          path: 'approvals/tracking-time',
          name: 'approval-tracking-time',
          component: () => import('@/views/approvals/TrackingTimeApprovalView.vue'),
          meta: { title: '轨迹审批' },
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
        {
          path: 'display-settings',
          name: 'display-settings',
          component: () => import('@/views/settings/DisplaySettingsView.vue'),
          meta: { title: '显示设置' },
        },
      ],
    },
  ],
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || 'Youzi'
  document.title = `${title} · Youzi`
  usePageTabs().openFromRoute(to)
})

export default router
