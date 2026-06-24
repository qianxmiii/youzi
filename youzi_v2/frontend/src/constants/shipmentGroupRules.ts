/** 运单分组规则类型（与后端 shipment_group_rules.py 一致） */

export const SHIPMENT_GROUP_RULE_OPTIONS = [
  {
    value: 'BATCH_DELIVERY_DEADLINE',
    label: '签收期限提醒',
    description: '同组首票签收后，未签收运单在期限前/超期提醒',
    defaultThresholdDays: 30,
    defaultWarningDays: 7,
  },
  {
    value: 'GROUP_ARRIVED_PAYMENT',
    label: '整组到港催款',
    description: '组内全部到港且未付清时提醒催款',
    defaultThresholdDays: null,
    defaultWarningDays: null,
  },
  {
    value: 'SINGLE_IN_TRANSIT_ETA_WARNING',
    label: '单票在途到港预警',
    description: '客户仅有一票在途时，按 ETA 提前 N 天提醒到港',
    defaultThresholdDays: null,
    defaultWarningDays: 10,
  },
] as const

export type ShipmentGroupRuleType = (typeof SHIPMENT_GROUP_RULE_OPTIONS)[number]['value']

export type ShipmentGroupAlertRuleKind = 'delivery' | 'payment' | 'arrival' | 'default'

/** 提醒卡片视觉分类 */
export function shipmentGroupAlertRuleKind(
  ruleType: string | null | undefined,
): ShipmentGroupAlertRuleKind {
  const key = (ruleType || '').trim().toUpperCase()
  if (key === 'BATCH_DELIVERY_DEADLINE') return 'delivery'
  if (key === 'GROUP_ARRIVED_PAYMENT' || key === 'LAST_BATCH_ARRIVED_PAYMENT') return 'payment'
  if (key === 'SINGLE_IN_TRANSIT_ETA_WARNING') return 'arrival'
  return 'default'
}

export function shipmentGroupRuleHasDeadlineFields(ruleType: string): boolean {
  return ruleType === 'BATCH_DELIVERY_DEADLINE'
}

export function shipmentGroupRuleHasEtaWarningFields(ruleType: string): boolean {
  return ruleType === 'SINGLE_IN_TRANSIT_ETA_WARNING'
}

const LABEL_MAP = Object.fromEntries(
  SHIPMENT_GROUP_RULE_OPTIONS.map((o) => [o.value, o.label]),
) as Record<ShipmentGroupRuleType, string>

export function shipmentGroupRuleLabel(ruleType: string | null | undefined): string {
  const key = (ruleType || '').trim().toUpperCase()
  if (key === 'LAST_BATCH_ARRIVED_PAYMENT') return LABEL_MAP.GROUP_ARRIVED_PAYMENT
  return LABEL_MAP[key as ShipmentGroupRuleType] ?? key
}

export function shipmentGroupRuleSelectOptions() {
  return SHIPMENT_GROUP_RULE_OPTIONS.map((o) => ({
    label: o.label,
    value: o.value,
  }))
}

export function defaultRuleDraft(ruleType: ShipmentGroupRuleType) {
  const meta = SHIPMENT_GROUP_RULE_OPTIONS.find((o) => o.value === ruleType)
  return {
    ruleType,
    enabled: true,
    thresholdDays: meta?.defaultThresholdDays ?? null,
    warningDays: meta?.defaultWarningDays ?? null,
    triggerStatus: '',
    configJson: '{}',
  }
}

/** 列表展示：按规则配置顺序排列启用规则 */
export function sortShipmentGroupEnabledRules(rules: string[]): string[] {
  const order = SHIPMENT_GROUP_RULE_OPTIONS.map((o) => o.value)
  const rank = new Map(order.map((v, i) => [v, i]))
  return [...rules].sort((a, b) => {
    const ai = rank.get(a as ShipmentGroupRuleType) ?? 99
    const bi = rank.get(b as ShipmentGroupRuleType) ?? 99
    return ai - bi || a.localeCompare(b)
  })
}
