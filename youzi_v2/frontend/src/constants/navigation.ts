export interface NavItem {
  name: string
  to: string
  icon: string
  badge?: string
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

export const navGroups: NavGroup[] = [
  {
    label: '工作台',
    items: [{ name: '概览', to: '/', icon: 'grid' }],
  },
  {
    label: '报价',
    items: [
      { name: '箱规计算', to: '/box', icon: 'box', badge: '待迁' },
      { name: '单地址报价', to: '/quote', icon: 'quote', badge: '待迁' },
      { name: '批量报价', to: '/quote/batch', icon: 'layers', badge: '待迁' },
      { name: '成本计算', to: '/cost', icon: 'calc', badge: '待迁' },
    ],
  },
  {
    label: '资料',
    items: [
      { name: '资料库', to: '/library', icon: 'book', badge: '待迁' },
      { name: '地址簿', to: '/addresses', icon: 'pin', badge: '待迁' },
    ],
  },
  {
    label: '运维',
    items: [
      { name: '运单管理', to: '/shipments', icon: 'truck' },
      { name: '船期监控', to: '/vessel-schedules', icon: 'layers' },
      { name: '统计管理', to: '/statistics', icon: 'chart' },
      { name: '客户管理', to: '/customers', icon: 'users' },
      { name: '渠道管理', to: '/channels', icon: 'layers' },
      { name: '计划任务', to: '/scheduled-tasks', icon: 'clock' },
      { name: '后台管理', to: '/admin', icon: 'settings' },
    ],
  },
]
