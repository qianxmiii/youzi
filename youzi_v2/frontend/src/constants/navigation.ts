export interface NavItem {
  name: string
  /** 有 children 时为空，仅作分组 */
  to: string
  icon: string
  badge?: string
  children?: NavItem[]
}

export interface NavGroup {
  label: string
  /** 一级分组图标（NavIcon 键名） */
  icon: string
  items: NavItem[]
}

export const navGroups: NavGroup[] = [
  {
    label: '工作台',
    icon: 'group-workbench',
    items: [{ name: '概览', to: '/', icon: 'grid' }],
  },
  {
    label: '报价中心',
    icon: 'group-quote',
    items: [
      { name: '报价跟进', to: '/quote-center/followups', icon: 'quote' },
      // 未迁移：箱规计算 / 单地址报价 / 批量报价；成本计算暂一并隐藏
      // { name: '箱规计算', to: '/box', icon: 'box', badge: '待迁' },
      // { name: '单地址报价', to: '/quote', icon: 'quote', badge: '待迁' },
      // { name: '批量报价', to: '/quote/batch', icon: 'layers', badge: '待迁' },
      // { name: '成本计算', to: '/cost', icon: 'calc' },
    ],
  },
  {
    label: '资料中心',
    icon: 'group-library',
    items: [
      // 未迁移：资料库暂隐藏
      // { name: '资料库', to: '/library', icon: 'book', badge: '待迁' },
      { name: '地址簿', to: '/addresses', icon: 'pin' },
    ],
  },
  {
    label: '运单中心',
    icon: 'group-shipment',
    items: [
      { name: '运单管理', to: '/shipments', icon: 'truck' },
      { name: '异常跟踪', to: '/shipment-exceptions', icon: 'alert' },
      { name: '催款管理', to: '/shipments/payment-reminders', icon: 'wallet' },
      { name: '运单分组', to: '/shipment-groups', icon: 'layers' },
      { name: '船期监控', to: '/vessel-schedules', icon: 'ship' },
    ],
  },
  {
    label: '客户中心',
    icon: 'group-customer',
    items: [{ name: '客户管理', to: '/customers', icon: 'users' }],
  },
  {
    label: '审批管理',
    icon: 'group-approval',
    items: [{ name: '轨迹审批', to: '/approvals/tracking-time', icon: 'approval' }],
  },
  {
    label: '数据中心',
    icon: 'group-data',
    items: [{ name: '统计管理', to: '/statistics', icon: 'chart' }],
  },
  {
    label: '常用工具',
    icon: 'group-tools',
    items: [{ name: '工具中心', to: '/tools', icon: 'wrench' }],
  },
  {
    label: '系统管理',
    icon: 'group-system',
    items: [
      { name: '计划任务', to: '/scheduled-tasks', icon: 'clock' },
      {
        name: '设置',
        to: '',
        icon: 'settings',
        children: [{ name: '显示设置', to: '/display-settings', icon: 'globe' }],
      },
    ],
  },
  {
    label: '后台管理',
    icon: 'settings',
    items: [{ name: '码表', to: '/admin', icon: 'settings' }],
  },
]
